import sys
import json
from df import df_worklist, ANALYSES, fmt, interp
from form_blocks import form_blocks
import cfg
from cfg_to_code import cfg_to_code
from util import fresh

def br_removal(blocks):
    in_, out = df_worklist(blocks, ANALYSES['cprop'])
    # overwirte blocks
    preds, succs = cfg.edges(blocks)
    for index, block in blocks.items():
        vals = out[index]
        if block[-1] is not None and block[-1]['op'] == 'br':
            guard = block[-1]['args'][0]
            if guard in vals:
                block[-1]['op'] = 'jmp'
                if vals[guard]:
                    block[-1]['args'] = [block[-1]['args'][1]]
                else:
                    block[-1]['args'] = [block[-1]['args'][2]]
    return blocks

def clean_cfg(blocks):
    changed = True
    while changed:
        preds, succs = cfg.edges(blocks)
        visited = dict.fromkeys(blocks.keys(),False)
        changed = _clean_cfg(blocks.keys()[0], blocks, preds, succs, visited)
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))
    return blocks


def _clean_cfg(block, blocks, preds, succs, visited):
    changed = False
    visited[block] = True
    for s in succs[block]:
        if not visited[s]:
            changed = changed or _clean_cfg(s, blocks, preds, succs, visited)
    

    if blocks[block][-1]['op'] == 'br' and blocks[block][-1]['args'][1] == blocks[block][-1]['args'][2]:
        next_block = blocks[block][-1]['args'][1]
        # eliminating redundant branches 
        # previous br both jump to this block 
        blocks[block][-1]['op'] = 'jmp'
        blocks[block][-1]['args'] = [blocks[block][-1]['args'][1]]
        succs[block].remove(next_block)
        preds[next_block].remove(block)
        # print(" eliminating redundant branches ")
        changed = True

        
    if len(blocks[block]) == 1 and blocks[block][-1]['op'] == 'jmp': 
        # eliminating empty blocks
       
        next_block = blocks[block][-1]['args'][0]
        for p in preds[next_block]:   
            succ = succs[p]
            if blocks[p][-1]['op'] == 'jmp': 
                blocks[p][-1]['args'] = [block]
                succ = [block] 
                preds[block].append(p)       
            else:
                #br
                args = blocks[p][-1]['args']
                for i in range(1,3):
                    if args[i] == next_block:
                        args[i] = block
                        succ.remove(next_block)
                        succ.append(block)
                        preds[block].append(p)

            succs[p] = succ

        blocks[block] = blocks[block][:-1] + blocks[next_block]
        del blocks[next_block]
        # print(" eliminating empty block")
        changed = True

    if len(succs[block]) == 1 and len(preds[succs[block][0]]) == 1:
        # eliminating non-empty blocks
        s = succs[block][0]
        blocks[block] = blocks[block][:-1] + blocks[s]
        del blocks[s]
        # print(" eliminating non empty block")
        changed = True
    
    return changed 


def unreachable_removal(blocks):
    preds, succs = cfg.edges(blocks)
    reachable = dict.fromkeys(blocks.keys(),False)
    reachable[blocks.keys()[0]] = True
    stack = [blocks.keys()[0]]
    while(len(stack) != 0):
        b = stack.pop() 
        for s in succs[b]:
            if not reachable[s]:
                reachable[s] = True
                stack.append(s)

    for b, r in reachable.items():
        if not r :
            del blocks[b]

    return blocks


def canonicalize(instr):
    if instr['op'] in ['add', 'mul', 'and', 'or']:
        instr['args'] = sorted(instr['args'])
    return json.dumps(instr, sort_keys=True)

def merge(block1, block2, names, from_start):
    l = 0
    for i in range(len(block1)):
        if from_start:
            instr1 = block1[l]
            instr2 = block2[l]
        else:
            instr1 = block1[len(block1) - l - 1]
            instr2 = block2[len(block2) - l - 1]
        if canonicalize(instr1) != canonicalize(instr2):
            break
        l +=1
    return fresh('t', names), l

def replace_target(blocks_r, all_blocks, orginals, new):
    for p in blocks_r:
        new_args = []
        for idx, arg in enumerate(all_blocks[p][-1]["args"]):
            if len(blocks[p][-1]["args"]) > 1 and idx == 0:
                # br gurad
                new_args.append(arg)
            elif arg in orginals:
                new_args.append(new)
            else:
                new_args.append(arg)
        all_blocks[p][-1]["args"] = new_args

def tail_merging_once(blocks):
    preds, succs = cfg.edges(blocks)
   
    bns = list(blocks.keys())
    for block in bns:
        count = {}
        # merge two preds
       
        for p in preds[block]:
            instr = blocks[p][-1]
            if instr is not None and instr['op'] == 'jmp':
                k = canonicalize(instr) 
                if k not in count:
                    count[k] = p
                else:
                    # find two blocks can be merged
                    b1 = blocks[count[k]]
                    b2 = blocks[p]
                    name, l = merge(b1, b2, list(blocks.keys()), from_start = False)
                    if l == 1:
                        continue
                    
                    if l == min(len(b1),len(b2)):
                        if len(b1) == len(b2):
                            replace_target(preds[count[k]] +  preds[p], blocks, [count[k], p], name)
                            del blocks[count[k]]
                            del blocks[p]
                            return True
                        if len(b1) < len(b2):
                            small_block = count[k]
                            large_block = p
                        else:   
                            small_block = p
                            large_block = count[k]

                        blocks[large_block] = blocks[large_block][:len(blocks[large_block]) - l]
                        jmp = {'op': 'jmp', "args": [small_block]} 
                        blocks[large_block].append(jmp)

                    else:
                        jmp = {'op': 'jmp', "args": [name]} 
                        new_block = b1[len(b1) - l:]
                        blocks[name] = new_block
                        blocks[count[k]] = b1[:len(b1) - l]
                        blocks[count[k]].append(jmp)
                        blocks[p] = b2[:len(b2) - l]
                        blocks[p].append(jmp)
                    return True                   
                    

        # merge two succs
        if blocks[block][-1] is not None and blocks[block][-1]['op'] == 'br':
            args = blocks[block][-1]['args']
            b1 = blocks[args[1]]
            b2 = blocks[args[2]]
            name, l = merge(b1, b2, list(blocks.keys()),from_start = True)
            if l > 0:  
                if l == len(b1):
                    # cannot have jmp in middle of block
                    # so this is the only case such that a block is entirely duplicated
                    jmp = {'op': 'jmp', "args": [args[1]]}
                    blocks[block] = blocks[block][:-1]
                    blocks[block].append(jmp)
                    replace_target(preds[args[2]], blocks, [args[2]], args[1])
                    del blocks[args[2]]
                else:
                    jmp = {'op': 'jmp', "args": [name]}
                    br = blocks[block][-1]
                    blocks[block] = blocks[block][:-1]
                    blocks[block].append(jmp)
                    replace_target(preds[args[1]] +  preds[args[2]], blocks, args[1:3], name)
                    blocks[name] = b1[:l]
                    blocks[args[1]] = b1[l:]
                    blocks[args[2]] = b2[l:]
                    blocks[name].append(br)
                return True
    

    return False

def tail_merging(blocks):

    while(tail_merging_once(blocks)):
        pass
        # print("=======================")
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))
    return blocks

if __name__ == '__main__':
    bril = json.load(sys.stdin)
    for func in bril['functions']:
        # Form the CFG.
        blocks = cfg.block_map(form_blocks(func['instrs']))
        cfg.add_terminators(blocks)
    
       
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))

        # br_removal(blocks)
        # print("================after br_removal ==================")
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))

        # unreachable_removal(blocks)
        # print("================after unreachable_removal ==================")
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))

        # clean_cfg(blocks)
        # print("================after clean_cfg ==================")
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))

        tail_merging(blocks)
        # print("================after tail_merging ==================")
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))

        # clean_cfg(blocks)
        # print("================after clean_cfg ==================")
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))
        print(cfg_to_code(blocks, func['name']))
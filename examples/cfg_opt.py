import sys
import json
from df import df_worklist, ANALYSES, fmt, interp
from form_blocks import form_blocks
import cfg
from cfg_to_code import cfg_to_code

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


if __name__ == '__main__':
    bril = json.load(sys.stdin)
    for func in bril['functions']:
        # Form the CFG.
        blocks = cfg.block_map(form_blocks(func['instrs']))
        cfg.add_terminators(blocks)
    
       
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))

        br_removal(blocks)
        # print("================after br_removal ==================")
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))

        unreachable_removal(blocks)
        # print("================after unreachable_removal ==================")
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))

        clean_cfg(blocks)
        # print("================after clean_cfg ==================")
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))

        print(cfg_to_code(blocks, func['name']))
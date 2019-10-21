import sys
import json
from df import df_worklist, ANALYSES, fmt, interp
from form_blocks import form_blocks
import cfg

def br_removal(blocks):
    in_, out = df_worklist(blocks, ANALYSES['cprop'])
    # overwirte blocks
    
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

if __name__ == '__main__':
    bril = json.load(sys.stdin)
    for func in bril['functions']:
        # Form the CFG.
        blocks = cfg.block_map(form_blocks(func['instrs']))
        cfg.add_terminators(blocks)
    
       
        for block in blocks:
            print('{}:'.format(block))
            print('{}:'.format(blocks[block]))

        br_removal(blocks)
        print("================after==================")
        for block in blocks:
            print('{}:'.format(block))
            print('{}:'.format(blocks[block]))

        unreachable_removal(blocks)
        print("================after==================")
        for block in blocks:
            print('{}:'.format(block))
            print('{}:'.format(blocks[block]))
import sys
import json
from df import df_worklist, ANALYSES, fmt, interp
from form_blocks import form_blocks
import cfg

def cfold(blocks):
    in_, out = df_worklist(blocks, ANALYSES['cprop'])
    # overwirte blocks
    for index, block in blocks.items():
        vals = in_[index]
        for instr_id, instr in enumerate(block):
            if instr['op'] == 'const':
                vals[instr['dest']] = instr['value']
            elif instr['op'] in interp and all(vals.get(arg, '?')!= '?' for arg in instr['args']):
                v =  interp[instr['op']](list(map(lambda arg: vals[arg], instr['args'])))
                block[instr_id]['op'] = 'const'
                block[instr_id]['value'] = v
                del block[instr_id]['args']
    return blocks

if __name__ == '__main__':
    bril = json.load(sys.stdin)
    for func in bril['functions']:
        # Form the CFG.
        blocks = cfg.block_map(form_blocks(func['instrs']))
        cfg.add_terminators(blocks)

       
        for block in blocks:
            print('{}:'.format(block))
            print('{}:'.format(blocks[block]))

        cfold(blocks)
        print("================after==================")
        for block in blocks:
            print('{}:'.format(block))
            print('{}:'.format(blocks[block]))

import sys
import json
from df import df_worklist, ANALYSES, fmt, interp
from form_blocks import form_blocks
import cfg
from cfg_to_code import cfg_to_code

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

def replace_args(args, vals):
    new_args = []
    for arg in args:
        if arg in vals:
            new_args.append(vals[arg])
        else:
            new_args.append(arg)
    return new_args

def copy_prop(blocks):
    in_, out = df_worklist(blocks, ANALYSES['copy'])
    # for block in blocks:
    #         print('{}:'.format(block))
    #         print('  in: ', fmt(in_[block]))
    #         print('  out:', fmt(out[block]))
    # overwirte blocks
    for index, block in blocks.items():
        out_vals = in_[index]
        for instr_id, instr in enumerate(block):
            if instr['op'] == 'br':
                instr['args'][0] = replace_args([instr['args'][0]], out_vals)[0]
            
            if instr['op'] == 'print':   
                instr['args'] = replace_args(instr['args'], out_vals)

            if 'dest' in instr:
                if 'args' in instr: 
                    instr['args'] = replace_args(instr['args'], out_vals)

                for k,v in out_vals.items():
                    if instr['dest'] == k or instr['dest'] == v:
                        del out_vals[k] 


                if instr['op'] == 'id':
                    out_vals[instr['dest']] = instr['args'][0]
              
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

        # cfold(blocks)
        # print("================after==================")
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))

        copy_prop(blocks)
        # print("================after==================")
        # for block in blocks:
        #     print('{}:'.format(block))
        #     print('{}:'.format(blocks[block]))
        print(cfg_to_code(blocks, func['name']))
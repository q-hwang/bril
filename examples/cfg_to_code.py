import json
import cfg

def cfg_to_code(blocks, f_name):
    preds, succs = cfg.edges(blocks)
    instrs = []
    for name, block in blocks.items():
        if len(instrs) != 0 and instrs[-1]['op'] == 'jmp' and instrs[-1]['args'][0] == name:
            instrs = instrs[:-1]
            if len(preds[name]) == 1:
                # this label is only for the fall through
                instrs+= block
                continue
        if len(preds[name]) != 0:
            instrs += [{"label": name}] 
        instrs+= block
    data = {'functions': [{"name": f_name}]}
    data['functions'][0]['instrs'] = instrs
    json_data = json.dumps(data, indent=2, sort_keys=True)
    return json_data

import json
import sys

data = json.load(open(sys.argv[1], 'r'))
main = data['functions'][0]['instrs']
main = [{'label': 'start'}] + main
blocks = []
cur_block = []
for i in main:
    if 'label' in i:
        if len(cur_block) > 0:
            blocks.append(cur_block)
            cur_block = []
            cur_block.append(i)
        else:
            cur_block.append(i)
    elif i['op'] in ['jmp', 'br']:
        cur_block.append(i)
        blocks.append(cur_block)
        cur_block = []
    else:
        cur_block.append(i)
if len(cur_block) > 0:
    blocks.append(cur_block)

labels = []
label_map = {}
ends = []
for idx, i in enumerate(blocks):
    labels.append(i[0])
    label_map[i[0]['label']] = idx
    ends.append(i[-1])

adj = [[] for i in range(len(labels))]
for idx, i in enumerate(ends):
    if i['op'] in ['jmp', 'br']:
        if i['op'] == 'jmp':
            for j in i['args']:
                adj[idx].append(label_map[j])
        else:
            for j in i['args'][1:]:
                adj[idx].append(label_map[j])
    else:
        adj[idx] = [idx+1]

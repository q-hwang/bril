import subprocess
import json
import numpy as np

def generate_grad_file(ts_file, input_vars, target):
    j = subprocess.check_output(["ts2bril", "f.ts"])
    
    eval_f = json.loads(j)
    grad_f = json.loads(j)
   
    eval_f["functions"][0]["args"] = input_vars
    grad_f["functions"][0]["args"] = input_vars

    eval_f["functions"][0]["instrs"].append({"op": "print", "args":[target]})
    grad_f["functions"][0]["instrs"].append({"op": "print_grad", "args":[target] + input_vars})
    return eval_f, grad_f 


def eval(f, inputs):
    f["functions"][0]["values"] = list(inputs)
    with open("f.json","w+") as fp:
        json.dump(f, fp,indent=2, sort_keys=True)

    with open("f.json","r+") as fr:
        j = subprocess.check_output("brili", stdin=fr)

    j = j.decode('utf-8')
    return np.array(list(map(float,j.strip().split())))
    
def optimize(eval_f, grad_f, x0, alpha):
    x = x0
    while np.linalg.norm(eval(grad_f, x)) > 1e-5:
        print(eval(eval_f, x))
        x = x - alpha * eval(grad_f, x) 
    return x


eval_f, grad_f = generate_grad_file("grad.ts", ["x", "m"], "y") 
# print(eval(eval_f, np.array([0.6])))
print(optimize(eval_f, grad_f, np.array([-0.6, 1]), 0.1))


import subprocess
import json
import numpy as np
import matplotlib.pyplot as plt

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
    NUM_ITERS=30
    x = x0
    vals = []
    pts = []
    iters = 0
    while True:
        eval_pt = eval(eval_f, x)
        print(eval_pt, x)
        vals.append(x[0])
        pts.append(eval_pt[0])
        x = x - alpha * eval(grad_f, x)
        iters += 1
        alpha *= 0.99
        # print(iters)
        if iters >= NUM_ITERS:
            break
    print(list(zip(vals, pts)))
    # plt.plot(vals, pts, '-^')
    # linspace = np.linspace(min(vals), max(vals), 50)
    # plt.plot(linspace, [abs(i) for i in linspace])
    # plt.show()
    return x


eval_f, grad_f = generate_grad_file("grad.ts", ["x", "m"], "y")
# print(eval(eval_f, np.array([0.6])))
print(optimize(eval_f, grad_f, np.array([-0.6, 1]), 0.2))


import torch
from torch.autograd import Variable


def f(x):
    y = 2*x
    z = x
    for i in range(5):
        with torch.enable_grad():
            loss = (z - y).abs()
            # print(z, y)
            grad = torch.autograd.grad(
                inputs = [z],
                outputs = loss,
                only_inputs = True,
                create_graph = True
            )
            z = z - 0.5 * grad[0]
    return z

x = torch.ones((1, 1))
x[0] = 3
x.requires_grad=True
for _ in range(10):
    output = f(x)
    loss = torch.nn.MSELoss()
    l = loss(output, 2*output)

    # x.grad -= x.grad
    l.backward()
    t = x.detach()
    t -= 0.5*x.grad
    x = t
    x.requires_grad=True



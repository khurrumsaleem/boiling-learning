from boiling_learning.utils.folded_functional import compose

def f(x):
    return x**2

def g(x):
    return x + 3

gof = compose(f, g)
print(gof(2))
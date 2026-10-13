from solution import route
assert route([('a','c',8),('a','b',2),('b','c',1)], 'a','c') == {'distance':3,'path':['a','b','c']}
assert route([('a','c',1),('a','b',1),('c','d',1),('b','d',1)], 'a','d') == {'distance':2,'path':['a','b','d']}
assert route([('a','b',1)], 'b','a') == {'distance':None,'path':[]}
assert route([], 'x','x') == {'distance':0,'path':['x']}
assert route([('a','b',1),('b','a',1),('b','z',4)], 'a','z') == {'distance':5,'path':['a','b','z']}
for weight in [0,-1,1.5,True]:
    try:
        route([('a','b',weight)], 'a','b')
    except ValueError:
        pass
    else:
        raise AssertionError('invalid weight accepted')
print('VERIFIER_PASS')

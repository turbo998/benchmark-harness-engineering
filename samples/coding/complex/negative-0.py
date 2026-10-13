def route(edges, start, target):
    for u, v, w in edges:
        if u == start and v == target:
            return {'distance': w, 'path': [start, target]}
    return {'distance': None, 'path': []}

import heapq
def route(edges, start, target):
    graph = {}
    for u, v, w in edges:
        if type(w) is not int or w <= 0:
            raise ValueError('weights must be positive integers')
        graph.setdefault(u, []).append((v, w))
    queue = [(0, (start,), start)]
    best = {}
    while queue:
        cost, path, node = heapq.heappop(queue)
        if node in best:
            continue
        best[node] = (cost, path)
        if node == target:
            return {'distance': cost, 'path': list(path)}
        for dest, weight in graph.get(node, []):
            if dest not in best:
                heapq.heappush(queue, (cost + weight, path + (dest,), dest))
    return {'distance': None, 'path': []}

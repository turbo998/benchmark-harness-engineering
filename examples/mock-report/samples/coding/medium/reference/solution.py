def merge(intervals):
    rows = sorted((int(a), int(b)) for a, b in intervals)
    if any(a > b for a, b in rows):
        raise ValueError('reversed interval')
    result = []
    for a, b in rows:
        if result and a <= result[-1][1]:
            result[-1][1] = max(result[-1][1], b)
        else:
            result.append([a, b])
    return result

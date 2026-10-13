from solution import merge
assert merge([]) == []
assert merge([[5, 7], [1, 3], [3, 6]]) == [[1, 7]]
assert merge([[1, 2], [3, 4]]) == [[1, 2], [3, 4]]
assert merge([[1, 9], [2, 3], [9, 9]]) == [[1, 9]]
try:
    merge([[3, 1]])
except ValueError:
    pass
else:
    raise AssertionError('reversed interval accepted')
print('VERIFIER_PASS')

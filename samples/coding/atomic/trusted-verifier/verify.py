from solution import slug
assert slug(' Hello, WORLD! ') == 'hello-world'
assert slug('A___B---C') == 'a-b-c'
assert slug('中文 Café 42') == 'caf-42'
assert slug('---') == ''
assert slug('a0B9') == 'a0b9'
print('VERIFIER_PASS')

import os, re

BASE = r'E:\Documents\Vibe-Coding\Reasoner'

def scan(path):
    for root, dirs, files in os.walk(path):
        if '__pycache__' in root or '.next' in root or 'node_modules' in root or 'healing' in root:
            continue
        for f in files:
            if f.endswith('.py'):
                yield os.path.join(root, f)

modules = {}
for fp in sorted(scan(BASE)):
    rel = os.path.relpath(fp, BASE)
    mod = rel.replace('\\', '.').replace('/', '.')[:-3]
    # strip leading . if any
    if mod.startswith('.'):
        mod = mod[1:]
    name = os.path.basename(fp)[:-3]
    modules[name] = mod

imports_to = {name: set() for name in modules}
for fp in sorted(scan(BASE)):
    rel = os.path.relpath(fp, BASE)
    name = os.path.basename(fp)[:-3]
    with open(fp, 'r', encoding='utf-8') as f:
        src = f.read()
    for other_name, other_mod in modules.items():
        if other_name == name:
            continue
        # match import other_name or from other_name import ... or from other_name.x import ...
        pattern = rf'^(?:import\s+{re.escape(other_name)}|from\s+{re.escape(other_name)}(?:\.[\w]+)?\s+import)'
        if re.search(pattern, src, re.MULTILINE):
            imports_to[name].add(other_name)

# reverse deps
reverse = {name: set() for name in modules}
for importer, imported_set in imports_to.items():
    for imported in imported_set:
        if imported in reverse:
            reverse[imported].add(importer)

with open('reverse_deps.txt', 'w', encoding='utf-8') as out:
    for name in sorted(reverse):
        deps = sorted(reverse[name])
        if deps:
            out.write(f'{name}: {", ".join(deps)}\n')

print('done')
import os, re, ast

BASE = r'E:\Documents\Vibe-Coding\Reasoner'

def scan(path):
    for root, dirs, files in os.walk(path):
        if '__pycache__' in root or '.next' in root or 'node_modules' in root:
            continue
        for f in files:
            if f.endswith('.py'):
                yield os.path.join(root, f)

def summary(filepath):
    rel = os.path.relpath(filepath, BASE)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            src = f.read()
    except Exception as e:
        return rel, f'ERROR: {e}', [], [], []
    m = re.search(r'^[\"\']{3}(.*?)[\"\']{3}', src, re.DOTALL)
    doc = m.group(1).strip().splitlines()[0] if m else ''
    try:
        tree = ast.parse(src)
    except SyntaxError:
        tree = None
    classes = []
    functions = []
    imports = []
    stdlib = {'os','sys','json','typing','asyncio','urllib','http','pathlib','re','math','random','datetime','collections','itertools','functools','hashlib','base64','enum','dataclasses','inspect','textwrap','statistics','warnings','traceback','uuid','string','time','copy','numbers','decimal','fractions','logging','csv','io','xml','html','difflib','unittest','pytest'}
    third = {'pydantic','fastapi','starlette','uvicorn','jinja2','markdown','requests','httpx','aiohttp','numpy','pandas','tiktoken','openai','anthropic','google','ollama','sqlite3','psycopg','sqlalchemy','cryptography','jwt','bcrypt','passlib','sklearn','tensorflow','torch','bs4','lxml','pillow','cv2','zstandard'}
    if tree:
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split('.')[0]
                    if name not in stdlib and name not in third:
                        imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ''
                top = mod.split('.')[0]
                if top and top not in stdlib and top not in third:
                    imports.append(mod)
    return rel, doc, classes, functions, list(sorted(set(imports)))

with open('py_summaries.txt', 'w', encoding='utf-8') as out:
    for fp in sorted(scan(BASE)):
        rel, doc, classes, functions, imports = summary(fp)
        if rel.startswith('ui-next'):
            continue
        out.write(f'FILE:{rel}\n')
        out.write(f'DOC:{doc}\n')
        out.write(f'CLS:{chr(1).join(classes)}\n')
        out.write(f'FUN:{chr(1).join(functions)}\n')
        out.write(f'IMP:{chr(1).join(imports)}\n')
        out.write('---\n')

print('done')
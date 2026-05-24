import os, re

base = r'e:\Major NCC Website\Major NCC Website'
pages_dir = os.path.join(base, 'pages')

# All HTML files
all_files = ['index.html'] + [f'pages/{f}' for f in os.listdir(pages_dir) if f.endswith('.html')]
print('=== HTML FILES ===')
for f in sorted(all_files):
    path = os.path.join(base, f)
    size = os.path.getsize(path)
    print(f'  {f}  ({size:,} bytes)')

print()
print('=== KEY ASSETS ===')
key_assets = ['js/main.js','js/auth.js','js/api.js','js/dark-mode.js','js/three-badge.js','css/style.css','images/ncc_badge.png','manifest.json']
for a in key_assets:
    path = os.path.join(base, a)
    exists = os.path.exists(path)
    print(f'  {"OK" if exists else "MISSING":8}  {a}')

print()
print('=== NAV LINKS FROM INDEX.HTML ===')
with open(os.path.join(base, 'index.html'), encoding='utf-8') as f:
    content = f.read()
links = re.findall(r'href="(pages/[^"]+\.html)"', content)
for link in sorted(set(links)):
    path = os.path.join(base, link)
    exists = os.path.exists(path)
    print(f'  {"OK" if exists else "MISSING":8}  {link}')

print()
print('=== CROSS-PAGE LINK AUDIT ===')
broken = []
for fname in sorted(os.listdir(pages_dir)):
    if not fname.endswith('.html'):
        continue
    fpath = os.path.join(pages_dir, fname)
    with open(fpath, encoding='utf-8', errors='ignore') as f:
        c = f.read()
    links = re.findall(r'href="([^"#]+\.html)"', c)
    for link in links:
        if link.startswith('http'):
            continue
        if link.startswith('../'):
            target = os.path.join(base, link[3:])
        else:
            target = os.path.join(pages_dir, link)
        if not os.path.exists(target):
            broken.append(f'{fname} -> {link}')
if broken:
    for b in broken:
        print(f'  BROKEN: {b}')
else:
    print('  All cross-page links OK')

print()
print('=== SCRIPT TAG CHECK ===')
all_pages = [('index.html', os.path.join(base, 'index.html'))]
for fname in sorted(os.listdir(pages_dir)):
    if fname.endswith('.html'):
        all_pages.append((f'pages/{fname}', os.path.join(pages_dir, fname)))

missing_scripts = []
for name, fpath in all_pages:
    with open(fpath, encoding='utf-8', errors='ignore') as f:
        c = f.read()
    scripts = re.findall(r'src="(\.\.\/js\/[^"]+|js/[^"]+)"', c)
    for s in scripts:
        spath = os.path.join(base, s.replace('../', ''))
        if not os.path.exists(spath):
            missing_scripts.append(f'{name}: {s}')
if missing_scripts:
    for m in missing_scripts:
        print(f'  MISSING: {m}')
else:
    print('  All script references OK')

print()
print('=== NAVBAR AUTH BUTTONS CHECK ===')
has_signup = []
no_signup = []
for name, fpath in all_pages:
    if 'login.html' in name or 'signup.html' in name or 'admin' in name or 'cadet-portal' in name:
        continue
    with open(fpath, encoding='utf-8', errors='ignore') as f:
        c = f.read()
    if 'btn-nav-signup' in c or 'signup.html' in c:
        has_signup.append(name)
    else:
        no_signup.append(name)
print('  Pages WITH Login+SignUp:')
for p in has_signup:
    print(f'    OK  {p}')
if no_signup:
    print('  Pages MISSING SignUp button:')
    for p in no_signup:
        print(f'    !!  {p}')

print()
print('=== DONE ===')

"""mock_model.py — موديل وهمي للتجربة من غير مفتاح (MOCK=1). مش بيرسم فعلاً، بيرجّع تصاميم من gold.json."""
import json, random, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = list(json.load(open(os.path.join(ROOT, 'gold.json'))).values())
NAMES = {'rabbit': ('Rabbit', 'أرنب'), 'ارنب': ('Rabbit', 'أرنب'), 'cat': ('Cat', 'قطة'), 'قطة': ('Cat', 'قطة'),
         'fish': ('Fish', 'سمكة'), 'owl': ('Owl', 'بومة')}
SIL = '<rect x="1" y="0.5" width="1" height="2"/><path d="M1,3 A1,1 0 0 1 2,2 H3 A1,1 0 0 1 4,3 V4 H1 Z"/><polygon points="0,5 1,4 4,4 5,5"/>'


def _name(parts):
    for p in parts:
        if isinstance(p, str) and '"character"' in p:
            m = re.search(r'"character": "([^"]+)"', p)
            if m:
                k = m.group(1).strip().lower()
                return NAMES.get(k, (k.title(), k))
    return ('Thing', 'شيء')


def mock_ask(system, parts):
    import time as _t
    _t.sleep(float(os.environ.get("MOCK_DELAY", "0")))
    s = system[:40]
    if s.startswith('You see a 5x5 grid'):
        return json.dumps({'guesses': random.choice([['rabbit', 'cat'], ['cat', 'rabbit', 'owl'], ['bird']]), 'description': 'mock'})
    if s.startswith('A 5x5 tile icon was meant'):
        return json.dumps({'fix': 'make the ears longer'})
    if s.startswith('You are judging'):
        return json.dumps({'ranking': [2, 1, 3, 4], 'why': 'clearest'})
    if s.startswith('Image #1 is the ORIGINAL'):
        return json.dumps({'best': 2, 'why': 'applied the edit'})
    en, ar = _name(parts)
    if '# SYSTEM PROMPT — Recommended' in system:
        return json.dumps({'name_en': en, 'name_ar': ar, 'view': 'front', 'plan': 'x', 'svg': SIL})
    txt = ' '.join(p for p in parts if isinstance(p, str))
    if 'EDIT_EXISTING_DESIGN' in txt:
        req = json.loads(txt[txt.index('{'):])
        g = [r[:] for r in req['previous_grid']]
        r, c = random.randrange(5), random.randrange(5)
        g[r][c] = random.choice(['0a', '3a', '3b', '.', '11a'])
        return json.dumps({'name_en': req['character'], 'name_ar': 'x', 'grid': g}, ensure_ascii=False)
    return json.dumps({'name_en': en, 'name_ar': ar, 'grid': random.choice(GOLD)}, ensure_ascii=False)

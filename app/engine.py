"""engine.py — نفس الـ pipeline اللي في النوت بوك (تصميم ← بلاطات ← تعرّف أعمى ← حكم ← تصحيح)
لكن كموديول يتنادى من السيرفر، مع دالة جديدة: edit() لتعديل رسمة بتعليق من المستخدم.

الـ solver بيقرا catalog.json من الفولدر الحالي، فلازم السيرفر يعمل chdir لجذر الحزمة قبل ما يستورد ده.
"""
import json, re, io, time, os, random, threading
import concurrent.futures as cf
import cairosvg
from PIL import Image, ImageDraw
import solver

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = json.load(open(os.path.join(ROOT, 'catalog.json')))
TILE = {int(k): v['d'] for k, v in CAT['tiles'].items()}
ORI = {o['key']: o for o in CAT['orients']}


def _read(name):
    return open(os.path.join(ROOT, name), encoding='utf-8').read()


SYS1 = _read('SYSTEM_PROMPT_1_silhouette.md')      # الموديل يرسم silhouette
SYS2 = _read('SYSTEM_PROMPT_2_direct_tiles.md')    # الموديل يختار البلاطات
GOLD = json.load(open(os.path.join(ROOT, 'gold.json')))
SYS2 += ("\n\nHUMAN-DESIGNED GOLD EXAMPLES (style reference ONLY: note how few features are exaggerated, how triangles/"
         "quarter-discs shape the outline, how tile types are VARIED. Never copy a layout):\n"
         + "\n".join(json.dumps(g) for g in GOLD.values()))

BLIND = """You see a 5x5 grid of black geometric tiles forming a simple flat icon. WITHOUT any hint, say what it depicts.
Use the simplest everyday name (cat, bird, fish, dog, rabbit, owl, car, boat... not sparrow / kitten).
Reply with JSON only: {"guesses": ["most likely", "second guess", "third guess"], "description": "one short sentence: what you actually see (shapes, which parts are missing or unclear)"}"""

ADVISE = """A 5x5 tile icon was meant to depict a {name} but a viewer saw: {desc}
Look at the image and give ONE concrete fix to make it clearly a {name} (which cells/features to add, remove or move). Reply JSON only: {{"fix": "..."}}"""

JUDGE = """You are judging {n} candidate 5x5 geometric tile icons of a "{name}", shown side by side and numbered 1..{n}.
Rank them from the BEST to the WORST icon of a {name}. Judge like a child shown the icon: which one is clearest and most clearly a {name} and not some other animal/object?
Penalise: looks like another thing (arrow, rocket, cat instead of owl...), missing signature feature, noisy/random tiles, floating bits, a solid blob.
Reply JSON only: {{"ranking": [best_number, ..., worst_number], "why": "one short sentence on the winner"}}"""

JUDGE_EDIT = """Image #1 is the ORIGINAL 5x5 tile icon of a "{name}". Images #2..#{n} are edited versions.
The user asked for this change: "{comment}"
Pick the edited version that applies the requested change best while the icon is still clearly a {name} (clean tiles, no floating bits).
Reply JSON only: {{"best": number_between_2_and_{n}, "why": "one short sentence"}}"""

HINTS = ['side view facing left', 'side view facing right', 'front view, symmetric',
         'three-quarter view, exaggerate the head', 'emphasise the tail/back',
         'use many diagonal triangles for the outline', 'use curved quarter-discs for a rounder body']


# ---------------------------------------------------------------- رسم الشبكة (للمراجعة بالصورة)
def valid_grid(g):
    if not (isinstance(g, list) and len(g) == 5 and all(isinstance(r, list) and len(r) == 5 for r in g)):
        return False
    return all(k in ('.', '#') or k in ORI for r in g for k in r)


def cell_tf(o):
    t = ''
    if o['rot']:
        t += f"rotate({o['rot']} 50 50) "
    if o['flip']:
        t += 'translate(100 0) scale(-1 1)'
    return t.strip()


def grid_group(g, fill='#111'):
    s = ''
    for r in range(5):
        for c in range(5):
            k = g[r][c]
            inner = ''
            if k == '#':
                inner = f'<rect width="100" height="100" fill="{fill}"/>'
            elif k != '.':
                o = ORI[k]
                inner = (f'<g transform="{cell_tf(o)}"><path d="{TILE[o["tile"]]}" fill="{fill}" '
                         f'fill-rule="evenodd"/></g>')
            s += f'<g transform="translate({c * 100} {r * 100})">{inner}</g>'
    return s


def lines_svg(x0, y0, cs, color='#9aa1a8', w=1.5):
    out = ''
    for i in range(6):
        out += f'<line x1="{x0 + i * cs}" y1="{y0}" x2="{x0 + i * cs}" y2="{y0 + 5 * cs}" stroke="{color}" stroke-width="{w}"/>'
        out += f'<line x1="{x0}" y1="{y0 + i * cs}" x2="{x0 + 5 * cs}" y2="{y0 + i * cs}" stroke="{color}" stroke-width="{w}"/>'
    return out


def grid_png(g):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -10 520 520" width="520" height="520">'
           f'<rect x="-10" y="-10" width="520" height="520" fill="#fff"/>{grid_group(g)}{lines_svg(0, 0, 100, w=2)}</svg>')
    return cairosvg.svg2png(bytestring=svg.encode())


def parse_json(t):
    t = t.strip()
    t = re.sub(r'^```(?:json)?|```$', '', t, flags=re.M).strip()
    return json.loads(t[t.index('{'): t.rindex('}') + 1])


def quality(grid):
    """تقييم تلقائي: تنوّع البلاطات، عدد الخانات المليانة، وعدم وجود قطع عايمة."""
    cells = [(r, c, grid[r][c]) for r in range(5) for c in range(5) if grid[r][c] not in ('.', '')]
    n = len(cells)
    kinds = len({k for _, _, k in cells})
    s = 0.0
    s += min(kinds, 7) / 7 * 0.4
    s += 0.3 if 9 <= n <= 18 else 0.0
    pos = {(r, c) for r, c, _ in cells}
    floating = sum(1 for r, c in pos if not any((r + dr, c + dc) in pos for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))))
    s += 0.3 if floating == 0 else 0.0
    full = sum(1 for _, _, k in cells if k == '0a')
    if full > 9:
        s -= 0.3
    return s


class Engine:
    def __init__(self, api_key=None, workers=2, low_think=False, include_lite=False,
                 my_models=None, ask_fn=None, user_gold_path=None):
        self.workers = workers
        self.deadline_s = int(os.environ.get('JOB_DEADLINE', '600'))        # أقصى وقت لشخصية واحدة (بعده بنرجّع اللي خلص)
        self.ask_budget = int(os.environ.get('ASK_BUDGET', '240'))          # أقصى وقت لخطوة واحدة (نداء + إعادة محاولات)
        self.call_timeout = int(os.environ.get('CALL_TIMEOUT', '100'))      # أقصى وقت لنداء Gemini واحد (ثواني)
        self.fast_judges = True          # التقييم/الحكم/النصيحة بتفكير قليل (أسرع)، والتصميم والتعديل بتفكير كامل
        self.low_think = low_think
        self.include_lite = include_lite
        self.bad = set()
        self.cool = {}
        self.last = {}
        self.tl = threading.local()
        self.sys2 = SYS2
        self.user_gold_path = user_gold_path
        if user_gold_path and os.path.exists(user_gold_path):
            for g in json.load(open(user_gold_path)):
                self.sys2 += '\nUSER-APPROVED EXAMPLE (best style, never copy the layout): ' + json.dumps(g)
        self._ask_override = ask_fn               # للاختبار بدون مفتاح
        self.client = None
        self.models = []
        if ask_fn is None:
            from google import genai
            self.genai_types = __import__('google.genai.types', fromlist=['types'])
            self.client = genai.Client(api_key=api_key, http_options=self.genai_types.HttpOptions(timeout=self.call_timeout * 1000))
            try:
                self.models = my_models or self._discover()
            except Exception as e:
                self.log('Could not discover models: ' + str(e)[:150])
                self.models = my_models or []
            if not self.models:
                self.models = ['gemini-3-flash-preview', 'gemini-3-pro-preview']
        self.log('Models: ' + ', '.join(self.models[:10]) if self.models else 'Test mode (mock model)')

    # ------------------------------------------------------------ لوج لكل job
    def log(self, msg):
        f = getattr(self.tl, 'log', None)
        (f or print)(msg)

    def bind_log(self, f):
        self.tl.log = f

    # ------------------------------------------------------------ الاتصال بـ Gemini
    def _discover(self):
        names = []
        for m in self.client.models.list():
            n = m.name.replace('models/', '')
            acts = getattr(m, 'supported_actions', None) or []
            if n.startswith('gemini') and ('generateContent' in acts or not acts) \
               and not any(x in n for x in ['tts', 'image', 'embedding', 'live', 'audio', 'robotics', 'computer', 'learnlm', 'aqa']):
                names.append(n)
        if not self.include_lite:
            names = [n for n in names if 'lite' not in n]
        g3 = [n for n in names if n.startswith('gemini-3')]
        names = g3 or names

        def key(n):
            ver = re.findall(r'(\d+(?:\.\d+)?)', n)
            v = float(ver[0]) if ver else 0
            tier = 0 if 'flash' in n and 'lite' not in n else (1 if 'lite' in n else 2)
            return (tier, -v, n)
        return sorted(set(names), key=key)

    def _cfg(self, system, use_json, low):
        types = self.genai_types
        kw = dict(system_instruction=system, temperature=1.0)
        if use_json:
            kw['response_mime_type'] = 'application/json'
        if low:
            try:
                kw['thinking_config'] = types.ThinkingConfig(thinking_level='low')
            except Exception:
                pass
        return types.GenerateContentConfig(**kw)

    def ask(self, system, parts, json_out=True, rounds=3, low=None):
        if self._ask_override:
            self.last[threading.get_ident()] = 'mock'
            return self._ask_override(system, parts)
        t0 = time.time()
        dl = getattr(self.tl, 'deadline', None)
        end = min(t0 + self.ask_budget, dl) if dl else t0 + self.ask_budget

        def check():
            if time.time() > end:
                raise RuntimeError('Time limit reached for this step (Gemini is slow or overloaded right now)')
        for _rnd in range(rounds):
            check()
            live = [x for x in self.models if x not in self.bad]
            ready = [x for x in live if self.cool.get(x, 0) <= time.time()]
            if live and not ready:                      # كل الموديلات في فترة راحة (503): استني أقرب واحد
                w = min(30, max(1, min(self.cool[x] for x in live) - time.time()))
                w = min(w, max(0, end - time.time()))
                self.log(f'All models overloaded, waiting {w:.0f}s'); time.sleep(w)
                ready = live
            for m in ready:
                check()
                use_json = json_out
                low_m = self.low_think if low is None else low
                for _ in range(3):
                    try:
                        check()
                        tc = time.time()
                        r = self.client.models.generate_content(model=m, contents=parts, config=self._cfg(system, use_json, low_m))
                        self.log(f'[{m}] answered in {time.time() - tc:.0f}s')
                        self.last[threading.get_ident()] = m
                        return r.text
                    except Exception as e:
                        msg = str(e)
                        lw = msg.lower()
                        if low_m and 'thinking' in lw:
                            low_m = False
                            continue
                        if use_json and ('mime' in lw or 'json mode' in lw):
                            use_json = False
                            continue
                        if '404' in msg or 'not_found' in lw or 'not found' in lw or 'not supported' in lw or '403' in msg or 'permission' in lw:
                            self.bad.add(m)
                            self.log(f'Skipping {m} (not available)')
                            break
                        if '429' in msg or 'resource_exhausted' in lw or 'quota' in lw:
                            if 'limit: 0' in lw:
                                self.bad.add(m)
                                self.log(f'Skipping {m} (not available on your plan)')
                            else:
                                mm = re.search(r'retry in ([\d.]+)s|retryDelay[^\d]*(\d+)', msg)
                                wait = min(float(next(g for g in mm.groups() if g)) + 1, 65) if mm else 20
                                self.log(f'{m}: rate limit hit, waiting {wait:.0f}s')
                                if time.time() + wait > end:
                                    raise RuntimeError('Rate limit: out of time for this step. Your free quota may be exhausted, wait a few minutes.')
                                time.sleep(wait)
                                continue
                            break
                        if '503' in msg or 'unavailable' in lw or 'overloaded' in lw or 'high demand' in lw \
                                or 'timed out' in lw or 'timeout' in lw or 'deadline' in lw or '504' in msg:
                            self.cool[m] = time.time() + 45          # السيرفر زحمة أو بطيء: مانضربوش تاني 45 ثانية وجرّبي اللي بعده
                            self.log(f'{m} overloaded or too slow, trying the next model')
                            break
                        self.log(f'{m} temporary error: {msg[:100]}')
                        time.sleep(4)
            check()
            self.log('All models busy, waiting a bit...')
            time.sleep(min(15, max(0, end - time.time())))
        raise RuntimeError('All Gemini models failed. Try again shortly or check your API key.')

    def png_part(self, grid):
        if self._ask_override:
            return ('png', grid)
        return self.genai_types.Part.from_bytes(data=grid_png(grid), mime_type='image/png')

    # ------------------------------------------------------------ التقييم
    def recognise(self, name_en, grid):
        out = parse_json(self.ask(BLIND, [self.png_part(grid), 'What does this icon depict?'], low=True if self.fast_judges else None))
        gs = [str(g).lower().strip() for g in out.get('guesses', [])]
        key = name_en.lower().strip()
        rank = next((i for i, g in enumerate(gs) if key in g or (g and g in key)), None)
        score = {0: 10, 1: 7, 2: 5}.get(rank, 1)
        return float(score), out.get('description', '') + '  | guesses: ' + ', '.join(gs)

    def advise(self, name_en, grid, desc):
        out = parse_json(self.ask(ADVISE.format(name=name_en, desc=desc), [self.png_part(grid), 'Suggest the fix.'], low=True if self.fast_judges else None))
        return out.get('fix', '')

    def sheet(self, grids):
        ims = [Image.open(io.BytesIO(grid_png(g))).convert('RGB').resize((360, 360)) for g in grids]
        W = Image.new('RGB', (370 * len(ims), 400), 'white')
        d = ImageDraw.Draw(W)
        for i, im in enumerate(ims):
            W.paste(im, (i * 370 + 5, 38))
            try:
                d.text((i * 370 + 160, 8), f'#{i + 1}', fill='black', font_size=26)
            except TypeError:
                d.text((i * 370 + 160, 8), f'#{i + 1}', fill='black')
        b = io.BytesIO()
        W.save(b, 'PNG')
        if self._ask_override:
            return ('sheet', len(grids))
        return self.genai_types.Part.from_bytes(data=b.getvalue(), mime_type='image/png')

    def judge(self, name_en, cands):
        out = parse_json(self.ask(JUDGE.format(n=len(cands), name=name_en),
                                  [self.sheet([c['grid'] for c in cands]), 'Rank them.']))   # الحكم بتفكير كامل: هو اللي بيفرّق بين الواضح والمبهم
        order = [int(x) - 1 for x in out.get('ranking', []) if 0 < int(x) <= len(cands)]
        for pos, i in enumerate(order):
            cands[i]['score'] += {0: 4, 1: 2.5, 2: 1}.get(pos, 0)
        self.last_order = order
        return out.get('why', '')

    # ------------------------------------------------------------ التصميم
    def design(self, name, mode, feedback=None, prev_grid=None):
        msg = {"character": name, "variation": random.choice(HINTS) + f' (seed {random.randint(1, 9999)})'}
        if feedback:
            msg["feedback_on_previous_attempt"] = feedback
        parts = [json.dumps(msg, ensure_ascii=False)]
        if prev_grid:
            parts = [self.png_part(prev_grid), 'This is your previous attempt (rendered). ' + parts[0]]
        d = None
        for _try in range(2):                                 # لو الـ JSON باظ نحاول مرة تانية
            try:
                d = parse_json(self.ask(SYS1 if mode == 'silhouette' else self.sys2, parts))
                break
            except (ValueError, KeyError):
                if _try:
                    raise
        grid = solver.solve(solver.rast(d['svg']))[0] if mode == 'silhouette' else d['grid']
        if not valid_grid(grid):
            raise ValueError('invalid grid from model')
        return {'model': self.last.get(threading.get_ident(), '?'), 'mode': mode,
                'name_en': d.get('name_en', name), 'name_ar': d.get('name_ar', ''), 'grid': grid}

    @staticmethod
    def _mode_for(k, modes):
        if modes == 'direct':
            return 'direct'
        if modes == 'silhouette':
            return 'silhouette'
        return 'silhouette' if k % 2 == 0 else 'direct'          # mix

    def _gen(self, name, n, modes='mix', on_cand=None):
        """بيطلّع n تصميم. on_cand(c) بيتنادى لكل تصميم أول ما يخلص (عشان الصفحة تعرضه من غير ما تستنى الباقي)."""
        parent_log = getattr(self.tl, 'log', None)
        deadline = getattr(self.tl, 'deadline', None)

        def one(k):
            self.tl.log = parent_log
            self.tl.deadline = deadline
            c = self.design(name, self._mode_for(k, modes))
            try:
                c['score'], c['problems'] = self.recognise(c['name_en'], c['grid'])
            except Exception as e:                    # فشل التقييم مايضيّعش تصميم سليم
                self.log(f'Could not score design #{k + 1} ({str(e)[:60]}); keeping it unscored')
                c['score'], c['problems'] = 1.0, ''
            c['score'] += quality(c['grid']) * 0.3
            c['kind'] = 'gen'
            return c

        cands = []
        ex = cf.ThreadPoolExecutor(max_workers=self.workers)
        try:
            futs = {ex.submit(one, k): k for k in range(n)}
            for f in cf.as_completed(futs):
                k = futs[f]
                try:
                    c = f.result()
                except Exception as e:
                    self.log(f'Design #{k + 1} failed: {str(e)[:100]}')
                    continue
                cands.append(c)
                self.log(f'Design #{k + 1} ({c["mode"]}) ready, score {c["score"]:.1f}')
                if on_cand:
                    on_cand(c)
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
        return cands

    def more(self, name_en, base_grid, n=3, modes='mix', on_cand=None):
        """محاولات إضافية لنفس الشخصية. الحكم بيقارنها بالنسخة الحالية، ولو واحدة أحسن منها بترجع كـ winner."""
        self.tl.deadline = time.time() + self.deadline_s
        cands = self._gen(name_en, n, modes, on_cand)
        if not cands:
            raise RuntimeError('No design succeeded. Try again.')
        winner = None
        try:
            base = {'grid': base_grid, 'score': 0.0, 'name_en': name_en}
            allc = [base] + cands
            self.log('Judge: ' + self.judge(name_en, allc))
            top = self.last_order[0] if getattr(self, 'last_order', None) else 0
            if top >= 1:
                winner = top - 1
        except Exception as e:
            self.log('Judge failed: ' + str(e)[:100])
            winner = max(range(len(cands)), key=lambda i: cands[i]['score'])
        return cands, winner

    def make_card(self, name, n=4, refine=True, target=7, modes='mix', on_cand=None):
        """بيرجّع (best, cands). كل مرشّح فيه: grid, score, model, mode, kind"""
        t0 = time.time()
        self.tl.deadline = t0 + self.deadline_s
        cands = self._gen(name, n, modes, on_cand)
        if not cands:
            raise RuntimeError('No design succeeded. Try again.')
        if len(cands) >= 2:
            try:
                self.log('Judge: ' + self.judge(cands[0]['name_en'], cands))
            except Exception as e:
                self.log('Judge failed: ' + str(e)[:100])
        best = max(cands, key=lambda c: c['score'])
        if refine and best['score'] < target:                 # جولة تصحيح واحدة
            try:
                self.log('Running a refine round...')
                fix = self.advise(best['name_en'], best['grid'], best['problems'])
                c = self.design(name, best['mode'], feedback='It looked like: ' + best['problems'] + ' FIX: ' + fix, prev_grid=best['grid'])
                c['score'], c['problems'] = self.recognise(c['name_en'], c['grid'])
                c['score'] += quality(c['grid']) * 0.3
                c['kind'] = 'refined'
                cands.append(c)
                self.log(f'After refine: score {c["score"]:.1f}')
                if c['score'] > best['score']:
                    best = c
            except Exception as e:
                self.log('Refine failed: ' + str(e)[:100])
        self.log(f'Total time: {time.time() - t0:.0f}s')
        return best, cands

    # ------------------------------------------------------------ تعديل بتعليق المستخدم
    def edit(self, name_en, name_ar, grid, comment, variants=2):
        """المستخدم يكتب تعليق ← الموديل يعدّل الشبكة الحالية. بنطلّع variants نسخ ونختار الأقرب للطلب."""
        parent_log = getattr(self.tl, 'log', None)
        self.tl.deadline = time.time() + self.deadline_s
        deadline = self.tl.deadline
        req = {
            "task": "EDIT_EXISTING_DESIGN",
            "character": name_en,
            "user_edit_request": comment,
            "previous_grid": grid,
            "rules": ("Apply the user's request to the previous design. Keep everything the user did not mention "
                      "the same, unless a neighbouring cell must change so the picture stays clean and clearly a "
                      f"{name_en}. Use ONLY catalog keys. Return the full JSON (name_en, name_ar, grid)."),
        }
        txt = json.dumps(req, ensure_ascii=False)

        def one(_k):
            self.tl.log = parent_log
            self.tl.deadline = deadline
            parts = [self.png_part(grid), 'This image is the CURRENT design (rendered). ' + txt]
            d = parse_json(self.ask(self.sys2, parts))
            g = d['grid']
            if not valid_grid(g):
                raise ValueError('invalid grid from model')
            return {'grid': g, 'mode': 'direct', 'model': self.last.get(threading.get_ident(), '?'),
                    'name_en': d.get('name_en', name_en), 'name_ar': d.get('name_ar', name_ar)}

        outs = []
        with cf.ThreadPoolExecutor(max_workers=self.workers) as ex:
            futs = [ex.submit(one, k) for k in range(variants)]
            for k, f in enumerate(futs):
                try:
                    outs.append(f.result())
                    self.log(f'Edited version #{k + 1} ready')
                except Exception as e:
                    self.log(f'Version #{k + 1} failed: {str(e)[:100]}')
        outs = [o for o in outs if o['grid'] != grid] or outs     # استبعد النسخ اللي ماتغيرتش لو في غيرها
        if not outs:
            raise RuntimeError('The model could not apply the edit. Try rephrasing the comment.')
        pick = outs[0]
        if len(outs) >= 2:
            try:
                out = parse_json(self.ask(JUDGE_EDIT.format(name=name_en, comment=comment, n=len(outs) + 1),
                                          [self.sheet([grid] + [o['grid'] for o in outs]), 'Pick the best edit.']))
                i = int(out.get('best', 2)) - 2
                if 0 <= i < len(outs):
                    pick = outs[i]
                self.log('Pick: ' + str(out.get('why', '')))
            except Exception as e:
                self.log('Picking best edit failed, using the first: ' + str(e)[:80])
        pick['kind'] = 'edit'
        pick['comment'] = comment
        pick['score'] = 0.0
        return pick

    def like(self, grid):
        """مثال معتمد من المستخدم (بيتعلم منه الموديل بعد كده)"""
        self.sys2 += '\nUSER-APPROVED EXAMPLE (best style, never copy the layout): ' + json.dumps(grid)
        if self.user_gold_path:
            lst = json.load(open(self.user_gold_path)) if os.path.exists(self.user_gold_path) else []
            lst.append(grid)
            json.dump(lst, open(self.user_gold_path, 'w'))

"""server.py — صفحة المستخدم لمولّد كروت البلاطات.

تشغيل محلي:   GEMINI_API_KEY=xxx python app/server.py
في Colab:      شوفي خلايا النوت بوك (بتستدعي start_server).

المتغيرات (اختياري):
  LIB_DIR     فولدر المكتبة (الافتراضي: library جنب الحزمة). في Colab ضعيه على Google Drive عشان ما يضيعش.
  PORT        البورت (الافتراضي 8000)
  RATE_LIMIT  أقصى عدد طلبات توليد/تعديل لكل IP في الساعة (الافتراضي 20، 0 = من غير حد)
  MOCK        لو =1 بيشتغل بموديل وهمي من غير مفتاح (للتجربة)
"""
import os, sys, json, re, time, uuid, threading, unicodedata, collections, copy, tempfile
import concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)                      # solver.py بيقرا catalog.json من الفولدر الحالي
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from flask import Flask, jsonify, request, send_from_directory, abort
import engine as eng
from storage import make_store

DEFAULT_COLOR = '#58C3DF'
LANGS = ('both', 'ar', 'en')


# ---------------------------------------------------------------- المكتبة (ملفات JSON)
def norm(s):
    """تطبيع للبحث: عربي (تشكيل/همزات/ة/ى) + إنجليزي lower"""
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه').replace('ى', 'ي').replace('ـ', '')
    return re.sub(r'\s+', ' ', s).strip().lower()


class Library:
    """المكتبة بتتحفظ في store (ملفات أو S3/R2) وكمان في ذاكرة الـ process (cache) عشان العرض والبحث يبقوا سريعين.
    السيرفر لازم يكون process واحد (worker واحد) عشان الـ cache يفضل متطابق."""

    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.entries, self.drafts = {}, {}
        self._load('entries/', self.entries)
        self._load('drafts/', self.drafts)
        for did, d in list(self.drafts.items()):             # مسودات أقدم من أسبوع بتتمسح
            if time.time() - d.get('created', 0) > 7 * 86400:
                self.delete_draft(did)
            elif d.get('status') == 'running':               # السيرفر اتعمله restart وهي شغالة: اللي خلص يفضل
                d['status'] = 'done'
                self.save_draft(d)

    def _load(self, prefix, into):
        keys = [k for k in self.store.keys(prefix) if k.endswith('.json')]

        def one(k):
            try:
                return self.store.get(k)
            except Exception:
                return None
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for obj in ex.map(one, keys):
                if obj and 'id' in obj:
                    into[obj['id']] = obj

    @staticmethod
    def _ok(i):
        if not re.fullmatch(r'[a-z0-9]{6,32}', i or ''):
            abort(404)

    def get(self, eid):
        self._ok(eid)
        with self.lock:
            e = copy.deepcopy(self.entries.get(eid))
        if e:
            e.setdefault('card', True)               # كروت المكتبة القديمة كانت كروت
        return e

    def save(self, e):
        self._ok(e['id'])
        e['updated'] = time.time()
        with self.lock:
            self.store.put(f"entries/{e['id']}.json", e)
            self.entries[e['id']] = copy.deepcopy(e)

    def delete(self, eid):
        self._ok(eid)
        with self.lock:
            self.store.delete(f'entries/{eid}.json')
            self.entries.pop(eid, None)

    def all(self):
        with self.lock:
            return sorted(self.entries.values(), key=lambda e: -e.get('created', 0))

    def get_draft(self, did):
        self._ok(did)
        with self.lock:
            return copy.deepcopy(self.drafts.get(did))

    def save_draft(self, d):
        self._ok(d['id'])
        with self.lock:
            self.store.put(f"drafts/{d['id']}.json", d)
            self.drafts[d['id']] = copy.deepcopy(d)

    def delete_draft(self, did):
        self._ok(did)
        with self.lock:
            self.store.delete(f'drafts/{did}.json')
            self.drafts.pop(did, None)

    def drafts_all(self):
        with self.lock:
            return sorted(copy.deepcopy(list(self.drafts.values())), key=lambda d: d.get('created', 0))

    def update_draft(self, did, mutate):
        """تعديل آمن لمسودة (نتايج بتتضاف من thread والصفحة بتضيف للمكتبة من thread تاني)"""
        with self.lock:
            d = copy.deepcopy(self.drafts.get(did))
            if d is None:
                return None
            mutate(d)
            self.save_draft(d)
            return d

    def new_draft(self, query, cands, suggested=None, from_entry=None, status='done'):
        d = {'id': uuid.uuid4().hex[:12], 'query': query, 'created': time.time(),
             'candidates': [self.cand(c, names=True) for c in cands], 'suggested': suggested,
             'added': [], 'from_entry': from_entry, 'status': status}
        first = cands[suggested] if (cands and suggested is not None) else (cands[0] if cands else {})
        d['name_en'] = first.get('name_en', query)
        self.save_draft(d)
        return d

    def entry_from_cand(self, draft, idx, card=False):
        c = draft['candidates'][idx]
        n_en = c.get('name_en') or draft['name_en']
        n_ar = c.get('name_ar') or ''
        k = {x: c[x] for x in ('grid', 'score', 'model', 'mode', 'kind', 'comment', 'ts') if x in c}
        e = {'id': uuid.uuid4().hex[:12], 'query': draft['query'], 'created': time.time(),
             'name_en': n_en, 'name_ar': n_ar, 'orig_en': n_en, 'orig_ar': n_ar,
             'candidates': [k], 'selected': 0, 'card': bool(card), 'color': DEFAULT_COLOR, 'lang': 'both'}
        self.save(e)
        return e

    @staticmethod
    def cand(c, names=False):
        o = {'grid': c['grid'], 'score': round(float(c.get('score', 0)), 2), 'model': c.get('model', '?'),
             'mode': c.get('mode', ''), 'kind': c.get('kind', 'gen'), 'comment': c.get('comment', ''),
             'ts': time.time()}
        if names:
            o['name_en'] = c.get('name_en', '')
            o['name_ar'] = c.get('name_ar', '')
        return o

    @staticmethod
    def summary(e):
        c = e['candidates'][e['selected']]
        return {'id': e['id'], 'name_en': e['name_en'], 'name_ar': e['name_ar'], 'color': e['color'],
                'lang': e['lang'], 'card': e.get('card', True), 'grid': c['grid'], 'n': len(e['candidates']), 'created': e['created']}

    def search(self, q):
        qn = norm(q)
        res = []
        for e in self.all():
            if not qn:
                res.append(e)
                continue
            hay = ' | '.join(norm(x) for x in (e.get('query'), e.get('name_en'), e.get('name_ar'),
                                               e.get('orig_en'), e.get('orig_ar')))
            if qn in hay or any(w and w == qn for w in hay.split(' | ')):
                res.append(e)
        return res


# ---------------------------------------------------------------- التطبيق
def create_app(api_key=None, lib_dir=None, mock=False, workers=2, my_models=None, low_think=False,
               rate_limit=None, parallel_jobs=None):
    app = Flask(__name__, static_folder=os.path.join(HERE, 'static'), static_url_path='/static')
    store = make_store(lib_dir or os.environ.get('LIB_DIR') or os.path.join(ROOT, 'library'))
    lib = Library(store)
    gold_path = os.path.join(tempfile.gettempdir(), 'tilecards_gold_user.json')      # أمثلتك المعتمدة (بتتحفظ في الـ store كمان)
    g = store.get('gold_user.json')
    if g is not None:
        json.dump(g, open(gold_path, 'w'))
    elif os.path.exists(gold_path):
        os.remove(gold_path)
    if mock:
        from mock_model import mock_ask
        engine = eng.Engine(ask_fn=mock_ask, workers=workers, user_gold_path=gold_path)
    else:
        engine = eng.Engine(api_key=api_key, workers=workers, my_models=my_models, low_think=low_think,
                            user_gold_path=gold_path)
    # طابور: شغلة واحدة في المرة افتراضياً عشان الحد المجاني. في الباقة المدفوعة زوّديه (2 أو 3) عشان أكتر من شخصية تتعمل مع بعض
    pool = cf.ThreadPoolExecutor(max_workers=int(parallel_jobs or os.environ.get('JOBS', '1')))
    jobs = {}
    hits = collections.defaultdict(list)
    RL = int(os.environ.get('RATE_LIMIT', '20')) if rate_limit is None else rate_limit

    def limited():
        if not RL:
            return False
        # TRUST_CF=1: السيرفر وراء Cloudflare، فنثق في CF-Connecting-IP (من غيرها كل الزوار بيبانوا نفس الـ IP)
        h = request.headers
        ip = (h.get('CF-Connecting-IP') if os.environ.get('TRUST_CF') == '1' else None) or \
             h.get('X-Forwarded-For', request.remote_addr or '?').split(',')[0].strip()
        now = time.time()
        hits[ip] = [t for t in hits[ip] if now - t < 3600]
        if len(hits[ip]) >= RL:
            return True
        hits[ip].append(now)
        return False

    def start_job(fn):
        jid = uuid.uuid4().hex[:10]
        job = {'id': jid, 'status': 'queued', 'log': [], 'kind': None, 'ref': None, 'error': None, 'n': 0, 't': time.time()}
        jobs[jid] = job
        for old in [k for k, v in jobs.items() if time.time() - v['t'] > 6 * 3600]:
            jobs.pop(old, None)

        def run():
            job['status'] = 'running'
            engine.bind_log(lambda m: job['log'].append(m))
            try:
                job['kind'], job['ref'] = fn(job)
                job['status'] = 'done'
            except Exception as e:
                job['status'] = 'error'
                job['error'] = str(e)[:300]
        pool.submit(run)
        return job

    # ---- صفحات
    @app.get('/')
    def index():
        return send_from_directory(os.path.join(HERE, 'static'), 'index.html')

    @app.get('/api/catalog')
    def catalog():
        cat = eng.CAT
        return jsonify({'tiles': {k: v['d'] for k, v in cat['tiles'].items()},
                        'orients': {o['key']: [o['tile'], o['rot'], o['flip']] for o in cat['orients']}})

    # ---- المكتبة
    @app.get('/api/library')
    def library():
        q = request.args.get('q', '')
        return jsonify([lib.summary(e) for e in lib.search(q)][:200])

    @app.get('/api/entry/<eid>')
    def entry(eid):
        e = lib.get(eid)
        return jsonify(e) if e else abort(404)

    @app.patch('/api/entry/<eid>')
    def patch_entry(eid):
        e = lib.get(eid) or abort(404)
        d = request.get_json(force=True, silent=True) or {}
        if 'selected' in d and isinstance(d['selected'], int) and 0 <= d['selected'] < len(e['candidates']):
            e['selected'] = d['selected']
        if 'color' in d and re.fullmatch(r'#[0-9a-fA-F]{6}', str(d['color'])):
            e['color'] = d['color']
        if isinstance(d.get('card'), bool):
            e['card'] = d['card']
        if d.get('lang') in LANGS:
            e['lang'] = d['lang']
        for k in ('name_en', 'name_ar'):
            if k in d:
                e[k] = str(d[k])[:60]
        lib.save(e)
        return jsonify(e)

    @app.delete('/api/entry/<eid>')
    def del_entry(eid):
        lib.delete(eid)
        return jsonify({'ok': True})

    @app.post('/api/entry/<eid>/like')
    def like(eid):
        e = lib.get(eid) or abort(404)
        engine.like(e['candidates'][e['selected']]['grid'])
        try:
            store.put('gold_user.json', json.load(open(gold_path)))
        except Exception:
            pass
        return jsonify({'ok': True})

    # ---- توليد / تعديل
    @app.post('/api/generate')
    def generate():
        d = request.get_json(force=True, silent=True) or {}
        raw = d['names'] if isinstance(d.get('names'), list) else [d.get('name', '')]
        names, seen = [], set()
        for x in raw:                                   # قايمة شخصيات: بنشيل التكرار ونحدد 12 كحد أقصى
            s = str(x).strip()[:60]
            if s and norm(s) not in seen:
                seen.add(norm(s))
                names.append(s)
        names = names[:12]
        if not names:
            return jsonify({'error': 'Type at least one character name'}), 400
        n = max(1, min(int(d.get('n', 4) or 4), 6))
        refine = bool(d.get('refine', True))
        modes = d.get('modes') if d.get('modes') in ('mix', 'direct', 'silhouette') else 'mix'

        def make_fn(name):
            def fn(job):
                # المسودة بتتعمل من الأول وبتتملي تصميم ورا تصميم، فالصفحة تعرض اللي خلص من غير ما تستنى الباقي
                did = lib.new_draft(name, [], status='running')['id']
                job['kind'], job['ref'] = 'draft', did

                def on_cand(c):
                    def m(x):
                        x['candidates'].append(lib.cand(c, names=True))
                        x['name_en'] = x['candidates'][0].get('name_en') or x['name_en']
                    d = lib.update_draft(did, m)
                    job['n'] = len(d['candidates']) if d else job['n']
                try:
                    best, cands = engine.make_card(name, n=n, refine=refine, modes=modes, on_cand=on_cand)
                except Exception:
                    lib.delete_draft(did)
                    job['kind'] = job['ref'] = None
                    raise

                def fin(x):
                    x['candidates'] = [lib.cand(c, names=True) for c in cands]
                    x['suggested'] = cands.index(best)
                    x['name_en'] = best.get('name_en') or x['name_en']
                    x['status'] = 'done'
                lib.update_draft(did, fin)
                return 'draft', did
            return fn
        res = []
        for nm in names:
            if limited():
                res.append({'name': nm, 'error': 'Hourly request limit reached. Try again later.'})
                continue
            res.append({'name': nm, 'job': start_job(make_fn(nm))['id']})
        return jsonify({'jobs': res})

    @app.post('/api/entry/<eid>/edit')
    def edit(eid):
        e = lib.get(eid) or abort(404)
        d = request.get_json(force=True, silent=True) or {}
        comment = str(d.get('comment', '')).strip()[:500]
        if not comment:
            return jsonify({'error': 'Write a comment first'}), 400
        if limited():
            return jsonify({'error': 'Hourly request limit reached. Try again later.'}), 429
        # بنعدّل على النسخة المختارة وقت الطلب
        base = e['candidates'][e['selected']]['grid']

        def fn(job):
            c = engine.edit(e['name_en'], e['name_ar'], base, comment)
            fresh = lib.get(eid)
            fresh['candidates'].append(lib.cand(c))
            fresh['selected'] = len(fresh['candidates']) - 1
            lib.save(fresh)
            return 'entry', eid
        return jsonify({'job': start_job(fn)['id']})

    @app.post('/api/entry/<eid>/more')
    def more(eid):
        e = lib.get(eid) or abort(404)
        d = request.get_json(force=True, silent=True) or {}
        if limited():
            return jsonify({'error': 'Hourly request limit reached. Try again later.'}), 429
        n = max(1, min(int(d.get('n', 3) or 3), 6))
        modes = d.get('modes') if d.get('modes') in ('mix', 'direct', 'silhouette') else 'mix'
        base = e['candidates'][e['selected']]['grid']

        def fn(job):
            # المحاولات الجديدة بتطلع كنتايج منفصلة: إنتي اللي بتختاري تضيفي أنهي واحدة للمكتبة
            did = lib.new_draft(e['name_en'], [], from_entry=eid, status='running')['id']
            job['kind'], job['ref'] = 'draft', did

            def on_cand(c):
                d = lib.update_draft(did, lambda x: x['candidates'].append(lib.cand(c, names=True)))
                job['n'] = len(d['candidates']) if d else job['n']
            try:
                cands, winner = engine.more(e['name_en'], base, n=n, modes=modes, on_cand=on_cand)
            except Exception:
                lib.delete_draft(did)
                job['kind'] = job['ref'] = None
                raise

            def fin(x):
                x['candidates'] = [lib.cand(c, names=True) for c in cands]
                x['suggested'] = winner
                x['status'] = 'done'
            lib.update_draft(did, fin)
            return 'draft', did
        return jsonify({'job': start_job(fn)['id']})

    @app.get('/api/drafts')
    def drafts_list():
        """النتايج اللي لسه ماتضافتش بالكامل (عشان الصفحة ترجّعها لو اتعمل refresh)"""
        out = [d for d in lib.drafts_all() if len(d.get('added', [])) < len(d['candidates'])]
        return jsonify(out)

    @app.get('/api/draft/<did>')
    def draft_get(did):
        d = lib.get_draft(did)
        return jsonify(d) if d else abort(404)

    @app.post('/api/draft/<did>/add')
    def draft_add(did):
        d = lib.get_draft(did) or abort(404)
        body = request.get_json(force=True, silent=True) or {}
        idxs = sorted({i for i in body.get('indexes', []) if isinstance(i, int) and 0 <= i < len(d['candidates'])})
        if not idxs:
            return jsonify({'error': 'Select at least one image'}), 400
        card = bool(body.get('card'))
        ids = [lib.entry_from_cand(d, i, card)['id'] for i in idxs]
        lib.update_draft(did, lambda x: x.__setitem__('added', sorted(set(x.get('added', [])) | set(idxs))))
        return jsonify({'entries': ids})

    @app.delete('/api/draft/<did>')
    def draft_del(did):
        lib.delete_draft(did)
        return jsonify({'ok': True})

    @app.get('/api/job/<jid>')
    def job(jid):
        j = jobs.get(jid) or abort(404)
        pos = 0
        if j['status'] == 'queued':
            pos = 1 + sum(1 for x in jobs.values() if x['status'] == 'queued' and x['t'] < j['t'])
        return jsonify({'status': j['status'], 'log': j['log'][-40:], 'kind': j['kind'], 'ref': j['ref'],
                        'error': j['error'], 'n': j.get('n', 0), 'queue': pos, 'elapsed': int(time.time() - j['t'])})

    return app


def start_server(app, port=8000, host='0.0.0.0'):
    """بيشغّل Flask في thread (مناسب لـ Colab). بيرجّع الـ thread."""
    from werkzeug.serving import make_server
    srv = make_server(host, port, app, threaded=True)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    app.config['_srv'] = srv
    return t


if __name__ == '__main__':
    mock = os.environ.get('MOCK') == '1'
    key = os.environ.get('GEMINI_API_KEY')
    if not mock and not key:
        sys.exit('Set GEMINI_API_KEY (or MOCK=1 to try without a key)')
    a = create_app(api_key=key, mock=mock)
    a.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), threaded=True)

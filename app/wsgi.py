"""wsgi.py — للنشر: gunicorn --chdir app --workers 1 --threads 16 --timeout 120 -b 0.0.0.0:8000 wsgi:app
لازم worker واحد (الطابور والـ jobs في الذاكرة)، والـ threads هي اللي بتخدم أكتر من مستخدم."""
import os
from server import create_app
app = create_app(api_key=os.environ.get('GEMINI_API_KEY'), mock=os.environ.get('MOCK') == '1',
                 workers=int(os.environ.get('WORKERS', '2')))

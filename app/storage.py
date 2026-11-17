"""storage.py — مكان حفظ المكتبة: ملفات محلية (الافتراضي) أو S3 / Cloudflare R2.

لو المتغيرات دي موجودة بيستخدم S3 تلقائي:
  S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY   (و S3_REGION اختياري، الافتراضي auto، و S3_PREFIX اختياري)
ده المطلوب عشان المكتبة تفضل موجودة على استضافات قرصها مؤقت (زي Cloudflare Containers).
"""
import os, json


class LocalStore:
    def __init__(self, root):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _p(self, key):
        return os.path.join(self.root, *key.split('/'))

    def get(self, key):
        p = self._p(key)
        if not os.path.exists(p):
            return None
        return json.load(open(p, encoding='utf-8'))

    def put(self, key, obj):
        p = self._p(key)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'
        json.dump(obj, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
        os.replace(tmp, p)

    def delete(self, key):
        p = self._p(key)
        if os.path.exists(p):
            os.remove(p)

    def keys(self, prefix):
        d = self._p(prefix.rstrip('/'))
        return [prefix + f for f in os.listdir(d)] if os.path.isdir(d) else []


class S3Store:
    def __init__(self, endpoint, bucket, key_id, secret, region='auto', prefix=''):
        import boto3
        from botocore.config import Config
        self.c = boto3.client('s3', endpoint_url=endpoint, aws_access_key_id=key_id, aws_secret_access_key=secret,
                              region_name=region, config=Config(retries={'max_attempts': 4}, signature_version='s3v4'))
        self.bucket = bucket
        self.prefix = prefix.strip('/') + '/' if prefix.strip('/') else ''

    def get(self, key):
        try:
            r = self.c.get_object(Bucket=self.bucket, Key=self.prefix + key)
        except self.c.exceptions.NoSuchKey:
            return None
        return json.loads(r['Body'].read().decode('utf-8'))

    def put(self, key, obj):
        self.c.put_object(Bucket=self.bucket, Key=self.prefix + key, ContentType='application/json',
                          Body=json.dumps(obj, ensure_ascii=False).encode('utf-8'))

    def delete(self, key):
        self.c.delete_object(Bucket=self.bucket, Key=self.prefix + key)

    def keys(self, prefix):
        out = []
        for page in self.c.get_paginator('list_objects_v2').paginate(Bucket=self.bucket, Prefix=self.prefix + prefix):
            out += [o['Key'][len(self.prefix):] for o in page.get('Contents', [])]
        return out


def make_store(local_dir):
    e = os.environ
    if e.get('S3_BUCKET') and e.get('S3_ENDPOINT'):
        return S3Store(e['S3_ENDPOINT'], e['S3_BUCKET'], e.get('S3_ACCESS_KEY_ID'), e.get('S3_SECRET_ACCESS_KEY'),
                       region=e.get('S3_REGION', 'auto'), prefix=e.get('S3_PREFIX', ''))
    return LocalStore(local_dir)

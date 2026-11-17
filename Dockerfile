FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libcairo2 && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV LIB_DIR=/data/library PORT=8000
VOLUME /data
EXPOSE 8000
CMD ["sh","-c","gunicorn --chdir app --workers 1 --threads 16 --timeout 120 -b 0.0.0.0:${PORT} wsgi:app"]

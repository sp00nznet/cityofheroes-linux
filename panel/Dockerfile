# Shard admin panel (panel/app.py). Build context is the repo root, for addaccount.py's hash.
FROM python:3.13-slim
RUN pip install --no-cache-dir pymssql==2.3.7
COPY addaccount.py panel/app.py /app/
WORKDIR /app
USER nobody
CMD ["python3", "-u", "app.py"]

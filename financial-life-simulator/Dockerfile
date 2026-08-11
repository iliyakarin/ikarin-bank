FROM python:3.11-slim

RUN groupadd -r simgroup && useradd -r -g simgroup simuser

WORKDIR /app

COPY --chown=simuser:simgroup requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=simuser:simgroup . .

# SQLite dedup state needs a writable directory
RUN mkdir -p /app/data && chown simuser:simgroup /app/data

USER simuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]

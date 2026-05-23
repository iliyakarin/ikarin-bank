FROM python:3.11-slim

RUN groupadd -r mockgroup && useradd -r -g mockgroup mockuser

WORKDIR /app

COPY --chown=mockuser:mockgroup requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=mockuser:mockgroup . .

USER mockuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

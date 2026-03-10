FROM python:3.11-slim

# Create a non-root user
RUN groupadd -r gatewaygroup && useradd -r -g gatewaygroup gatewayuser

WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY --chown=gatewayuser:gatewaygroup requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=gatewayuser:gatewaygroup . .

USER gatewayuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]

FROM python:3.11-slim

# Create a non-root user
RUN groupadd -r simulatorgroup && useradd -r -g simulatorgroup simulatoruser

WORKDIR /app

COPY --chown=simulatoruser:simulatorgroup requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=simulatoruser:simulatorgroup . .

USER simulatoruser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

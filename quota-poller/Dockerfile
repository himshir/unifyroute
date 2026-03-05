FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY shared/ /app/shared/
RUN pip install -e /app/shared[asyncpg]

COPY quota-poller/ /app/quota-poller/
RUN pip install -e /app/quota-poller

# Copy router (imported by quota-poller at runtime)
COPY router/ /app/router/
RUN pip install -e /app/router

CMD ["python", "-m", "quota_poller.main"]

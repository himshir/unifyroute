FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY shared/ /app/shared/
RUN pip install -e /app/shared[asyncpg]

COPY credential-vault/ /app/credential-vault/
RUN pip install -e /app/credential-vault

EXPOSE 8001

CMD ["uvicorn", "credential_vault.main:app", "--host", "0.0.0.0", "--port", "8001"]

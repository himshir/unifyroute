FROM python:3.11-slim

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy shared package first (dependency of api-gateway)
COPY shared/ /app/shared/
RUN pip install -e /app/shared[asyncpg]

# Copy and install api-gateway
COPY api-gateway/ /app/api-gateway/
RUN pip install -e /app/api-gateway

# Copy router (imported by api-gateway at runtime)
COPY router/ /app/router/
RUN pip install -e /app/router

# Copy routing config
COPY router/routing.yaml /app/routing.yaml

EXPOSE 8000

CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]

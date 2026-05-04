# Langfuse Setup

Minimal Docker Compose setup for Langfuse.

## Quick Start

1. Copy `.env.example` to `.env` and update the credentials (especially CHANGEME values):
   ```bash
   cp .env.example .env
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

3. Access Langfuse Web UI at `http://localhost:3000`

## Admin UI Access

Access the Langfuse web UI at `http://localhost:3000` with:
- **Email**: `admin@example.com`
- **Password**: `admin123`

## Services

- **langfuse-web**: Main web interface (port 3000)
- **langfuse-worker**: Background worker service (port 3030)
- **postgres**: PostgreSQL database (port 5432, localhost only)
- **clickhouse**: ClickHouse analytics database (port 8123, localhost only)
- **minio**: S3-compatible storage (port 9090)
- **redis**: Redis cache (port 6379, localhost only)

## Important Security Notes

Before using in production, update these values in your `.env`:
- `NEXTAUTH_SECRET`
- `ENCRYPTION_KEY` (generate with: `openssl rand -hex 32`)
- `SALT`
- `POSTGRES_PASSWORD`
- `CLICKHOUSE_PASSWORD`
- `REDIS_AUTH`
- `MINIO_ROOT_PASSWORD`

## Stop Services

```bash
docker-compose down
```

To also remove volumes (delete data):
```bash
docker-compose down -v
```

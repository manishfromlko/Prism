# LiteLLM Setup

Minimal Docker Compose setup for LiteLLM with Langfuse callback integration.

## Quick Start

1. Copy `.env.example` to `.env` and update the values:
   ```bash
   cp .env.example .env
   ```

2. Update `litellm_config.yaml` with your model configurations if needed

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. Access LiteLLM Proxy at `http://localhost:4000`
5. Prometheus metrics at `http://localhost:9191`

## Admin UI Access

Access the LiteLLM admin UI at `http://localhost:4000/admin/` with:
- **Username**: `admin`
- **Password**: `sk-1234` (master key)

## Services

- **litellm**: LiteLLM proxy server (port 4000)
- **db**: PostgreSQL database (port 5442)
- **prometheus**: Prometheus for metrics (port 9191)

## Langfuse Integration

The setup is configured to send logs and traces to Langfuse via callbacks. Make sure to:

1. Have Langfuse running (see the `../langfuse` directory)
2. Update your Langfuse credentials in `.env`:
   - `LANGFUSE_PUBLIC_KEY`
   - `LANGFUSE_SECRET_KEY`
   - `LANGFUSE_BASE_URL`

## Configuration

Edit `litellm_config.yaml` to:
- Add more LLM models
- Configure custom callbacks
- Adjust settings as needed

## LLM Provider Setup

Update your `.env` with API keys for the LLM providers you want to use:
- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- Cohere: `COHERE_API_KEY`
- And others as needed

## Stop Services

```bash
docker-compose down
```

To remove volumes (delete data):
```bash
docker-compose down -v
```

## API Usage Example

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

All requests will be automatically logged to Langfuse.

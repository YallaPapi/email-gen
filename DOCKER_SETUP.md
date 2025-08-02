# Docker Setup for Scalable Email Generator

## Quick Start

1. **Create .env file** with your OpenAI API key:
   ```bash
   echo "OPENAI_API_KEY=your_key_here" > .env
   ```

2. **Build and start all services**:
   ```bash
   docker-compose up --build
   ```

## Services

The Docker setup includes:

- **Redis**: Message broker and backend storage
- **Backend**: FastAPI application (http://localhost:8000)
- **Worker1-4**: Four Celery workers, each using a different GPT-3.5 model:
  - Worker1: gpt-3.5-turbo
  - Worker2: gpt-3.5-turbo-0125
  - Worker3: gpt-3.5-turbo-1106
  - Worker4: gpt-3.5-turbo-16k
- **Flower**: Celery monitoring dashboard (http://localhost:5555)

## Benefits

- **40,000 requests/day**: Each model has a 10k daily limit
- **4x faster processing**: True parallel processing with 4 workers
- **Automatic failover**: If one model hits limits, others continue
- **Easy monitoring**: Flower dashboard shows worker status

## Commands

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up --build
```

## Monitoring

- Main app: http://localhost:8000
- Worker monitor: http://localhost:5555
- Model stats: http://localhost:8000/model-stats
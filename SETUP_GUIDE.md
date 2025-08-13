# Two-Step Email Generator - Setup Guide

## Overview
This system generates unique cold emails using a two-step AI process:
1. **Step 1**: Analyzes industry and creates base email with 3 AI solutions
2. **Step 2**: Rewrites with randomized instructions for maximum variation

Each email is completely unique - perfect for 5k+ daily campaigns.

## Quick Start

### Option 1: Docker (Recommended)
```bash
# 1. Set your OpenAI API key in .env
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 2. Start everything with Docker
docker-compose up -d

# 3. Open browser to http://localhost:5000
```

### Option 2: Local Setup (Windows)
```batch
# 1. Install Redis
# Download from: https://github.com/microsoftarchive/redis/releases
# Or use WSL: wsl --install

# 2. Set your OpenAI API key
set OPENAI_API_KEY=your-api-key-here

# 3. Run startup script
startup.bat

# 4. Open browser to http://localhost:5000
```

### Option 3: Local Setup (Mac/Linux)
```bash
# 1. Install Redis
brew install redis  # Mac
sudo apt-get install redis-server  # Ubuntu

# 2. Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# 3. Run startup script
chmod +x startup.sh
./startup.sh

# 4. Open browser to http://localhost:5000
```

## Configuration

### Required Environment Variables
Create a `.env` file:
```
OPENAI_API_KEY=sk-...your-key-here
REDIS_URL=redis://localhost:6379/0
```

### Optional Settings
```
CELERY_WORKERS=4          # Number of worker processes
CELERY_CONCURRENCY=2      # Tasks per worker
API_RATE_LIMIT=1          # Requests per second
```

## How It Works

### The Two-Step Process

**Step 1 - Industry Analysis:**
- AI analyzes the specific industry
- Identifies 3 real problems that industry faces
- Generates 3 AI solutions (always includes lead gen or chatbots)

**Step 2 - Variation Rewrite:**
- Applies one of 4 rewrite strategies randomly:
  - Tone variation (casual, friendly, conversational)
  - Direct variation (punchy, brief, straight to point)
  - Story variation (example, case study, results)
  - Natural variation (conversational, helpful, authentic)
- Changes opening, structure, and CTA
- Uses hash-based seeding for deterministic uniqueness

### Input CSV Format
Your CSV must have these columns:
- `first_name` - Contact's first name
- `organization_name` - Company name
- `industry` - Industry type (any industry works)
- `organization_short_description` - Brief company description (optional)

Example:
```csv
first_name,organization_name,industry,organization_short_description
John,ABC Corp,Software,B2B SaaS platform
Sarah,XYZ Medical,Healthcare,Multi-specialty clinic
```

## Scaling for 5k+ Emails/Day

### Performance Optimization
1. **Multiple Workers**: Default 4 workers × 2 concurrent = 8 parallel emails
2. **Rate Limiting**: 1 req/sec per worker = 8 emails/sec max
3. **Redis Queue**: Handles large batches efficiently

### Scaling Up
```bash
# Increase workers for more throughput
docker-compose up -d --scale worker=8

# Or in startup.bat, add more workers:
start /B celery -A backend.tasks worker -n worker3@%%h
start /B celery -A backend.tasks worker -n worker4@%%h
```

### Daily Limits
- OpenAI API limits vary by tier
- Monitor usage in OpenAI dashboard
- System auto-pauses at daily limit

## Testing

### Test with Sample Data
```python
# Run test script
python test_local_twostep.py

# Or use the web interface with test_industries.csv
```

### Verify Variation
Each email should have:
- Different opening style
- Different solution presentation
- Different CTA
- Unique structure

## Troubleshooting

### Redis Connection Error
```
Error: Cannot connect to redis://localhost:6379
```
**Solution**: Start Redis service
- Windows: `redis-server`
- Mac: `brew services start redis`
- Linux: `sudo service redis-server start`

### OpenAI API Key Error
```
Error: OpenAI API key not found
```
**Solution**: Set in .env file or environment:
- Windows: `set OPENAI_API_KEY=sk-...`
- Mac/Linux: `export OPENAI_API_KEY=sk-...`

### Rate Limit Errors
```
Error: Rate limit exceeded
```
**Solution**: Reduce workers or add delays in celeryconfig.py

## Production Deployment

### For AWS/Cloud
1. Use docker-compose.prod.yml
2. Set environment variables in cloud console
3. Use managed Redis (ElastiCache/Redis Cloud)
4. Scale workers based on load

### Security
- Never commit .env file
- Use secrets management in production
- Rotate API keys regularly
- Monitor usage and costs

## Support

### Logs
- Worker logs: `worker_logs.txt`
- Application logs: Check console output
- Redis monitoring: `redis-cli monitor`

### Common Issues
1. **Emails too similar**: Check hash seeding is working
2. **Slow processing**: Add more workers
3. **API errors**: Check API key and limits
4. **Memory issues**: Reduce batch size

## Advanced Features

### Custom Industries
The system handles ANY industry dynamically - no configuration needed.

### Variation Control
Modify `generate_rewrite_instructions()` in tasks.py to customize variation strategies.

### Model Selection
Change model in tasks.py:
- `gpt-3.5-turbo` (default, fast)
- `gpt-4` (better quality, slower)
- `gpt-4-turbo` (best quality)

---

## Ready to Scale!
The system is configured for high-volume email generation with maximum variation. Each recipient gets a unique, industry-specific email tailored to their business.
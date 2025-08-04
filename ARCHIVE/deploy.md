# Deployment Guide

## Option 1: VPS Deployment (DigitalOcean/AWS/Linode)

1. **Create a VPS** (Ubuntu 22.04 recommended)
2. **Install Docker**:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

3. **Clone and run**:
```bash
git clone <your-repo>
cd scalable_email_generator_fixed
echo "OPENAI_API_KEY=your_key_here" > .env
docker-compose -f docker-compose.prod.yml up -d
```

## Option 2: Push to Docker Hub

1. **Build and push images**:
```bash
# Tag and push backend
docker build -t yourusername/email-gen-backend ./backend
docker push yourusername/email-gen-backend

# Tag and push worker  
docker build -t yourusername/email-gen-worker ./backend
docker push yourusername/email-gen-worker
```

2. **On your server**, just run:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Option 3: Cloud-Specific Services

### AWS:
- **ECS (Elastic Container Service)**: Managed Docker containers
- **Fargate**: Serverless containers (no server management)
- **Elastic Beanstalk**: Simple Docker deployment

### Google Cloud:
- **Cloud Run**: Serverless containers
- **GKE**: Kubernetes if you need to scale huge

### Railway/Render/Fly.io:
- Modern platforms that deploy directly from GitHub
- Just connect repo and they handle everything

## Quick Railway Example:
1. Push code to GitHub
2. Connect Railway to your repo
3. Add services: Redis, Backend, Workers
4. Set environment variables
5. Deploy!

## Minimum Server Requirements:
- 2-4 GB RAM
- 2 vCPUs
- 20GB storage
- Ubuntu/Debian OS

## Domain Setup:
1. Point your domain to server IP
2. Use Cloudflare for free SSL
3. Or use Nginx as reverse proxy:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
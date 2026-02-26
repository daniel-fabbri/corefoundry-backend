# DEPLOYMENT.md

## Deployment Guide

This guide explains how to deploy CoreFoundry in different environments.

## Local Development

### 1. Prerequisites
- Python 3.10+
- PostgreSQL 12+
- Ollama installed and running

### 2. Setup

```bash
# Clone repository
git clone https://github.com/daniel-fabbri/corefoundry-backend.git
cd corefoundry-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
./init_db.sh

# Start development server
./dev.sh
```

## Docker Deployment

### Using Docker Compose

The easiest way to run CoreFoundry with all dependencies:

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
docker-compose ps

# Initialize database (one-time)
# First create a .env file with proper settings
docker-compose run --rm backend python -c "from corefoundry.app.db.connection import init_db; init_db()"

# Uncomment backend service in docker-compose.yml and start
docker-compose up -d backend

# View logs
docker-compose logs -f backend
```

### Manual Docker Build

```bash
# Build image
docker build -t corefoundry:latest .

# Run container
docker run -d \
  --name corefoundry \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://postgres:postgres@host:5432/corefoundry \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  corefoundry:latest
```

## Production Deployment

### Environment Variables

For production, set the following environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/corefoundry

# Ollama
OLLAMA_HOST=http://your-ollama-host:11434
OLLAMA_MODEL=llama2

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=false

# Optional: External URLs
NGROK_URL=https://your-app.ngrok.io
CLOUDFLARE_TUNNEL_URL=https://your-app.your-domain.com
```

### Using Systemd (Ubuntu/Debian)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/corefoundry.service
```

Add the following content:

```ini
[Unit]
Description=CoreFoundry Backend
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/corefoundry
Environment="PATH=/opt/corefoundry/venv/bin"
EnvironmentFile=/opt/corefoundry/.env
ExecStart=/opt/corefoundry/venv/bin/uvicorn corefoundry.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable corefoundry
sudo systemctl start corefoundry
sudo systemctl status corefoundry
```

### Using Nginx as Reverse Proxy

Install Nginx:

```bash
sudo apt-get install nginx
```

Create Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/corefoundry
```

Add:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/corefoundry /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL with Let's Encrypt

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Cloud Deployment

### AWS EC2

1. Launch an Ubuntu EC2 instance
2. Install dependencies:
   ```bash
   sudo apt-get update
   sudo apt-get install python3.10 python3.10-venv postgresql
   ```
3. Follow local development setup
4. Use systemd and nginx as described above
5. Configure security groups to allow:
   - Port 80 (HTTP)
   - Port 443 (HTTPS)
   - Port 22 (SSH)

### Google Cloud Platform

Similar to AWS, using Google Compute Engine:

```bash
gcloud compute instances create corefoundry \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud
```

### Heroku

Create `Procfile`:

```
web: uvicorn corefoundry.main:app --host 0.0.0.0 --port $PORT
```

Deploy:

```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

## Ollama Configuration

### Local Ollama

```bash
# Install
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2

# Start server
ollama serve
```

### Remote Ollama with ngrok

```bash
# Install ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Authenticate
ngrok config add-authtoken YOUR_TOKEN

# Expose Ollama
ngrok http 11434
```

Update `OLLAMA_HOST` in `.env` with the ngrok URL.

### Cloudflare Tunnel

```bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Create tunnel
cloudflared tunnel create corefoundry-ollama
cloudflared tunnel route dns corefoundry-ollama ollama.your-domain.com
cloudflared tunnel run corefoundry-ollama
```

## Monitoring

### Health Check

The `/health` endpoint provides status information:

```bash
curl http://localhost:8000/health
```

### Logging

For production, configure proper logging:

```python
# In configs/settings.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/corefoundry/app.log'),
        logging.StreamHandler()
    ]
)
```

### Monitoring Tools

- **Prometheus**: Add prometheus-fastapi-instrumentator
- **Grafana**: Visualize metrics
- **Sentry**: Error tracking

## Database Migrations

For production, use Alembic for database migrations:

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

## Security Checklist

- [ ] Use strong database passwords
- [ ] Enable SSL/TLS
- [ ] Configure CORS properly
- [ ] Use environment variables for secrets
- [ ] Enable rate limiting
- [ ] Implement authentication
- [ ] Keep dependencies updated
- [ ] Regular backups
- [ ] Monitor logs
- [ ] Use firewall rules

## Backup

### PostgreSQL Backup

```bash
# Backup
pg_dump -U postgres corefoundry > backup.sql

# Restore
psql -U postgres corefoundry < backup.sql
```

### Automated Backups

Create a cron job:

```bash
0 2 * * * /usr/bin/pg_dump -U postgres corefoundry > /backups/corefoundry-$(date +\%Y\%m\%d).sql
```

## Scaling

### Horizontal Scaling

Use multiple backend instances behind a load balancer:

```bash
# Start multiple instances
uvicorn corefoundry.main:app --port 8001
uvicorn corefoundry.main:app --port 8002
uvicorn corefoundry.main:app --port 8003
```

Configure Nginx load balancing:

```nginx
upstream corefoundry_backend {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    location / {
        proxy_pass http://corefoundry_backend;
    }
}
```

### Database Scaling

- Use connection pooling (already configured in SQLAlchemy)
- Consider read replicas for heavy read workloads
- Use PostgreSQL partitioning for large tables

## Troubleshooting

### Common Issues

1. **Database connection errors**
   - Check DATABASE_URL
   - Verify PostgreSQL is running
   - Check firewall rules

2. **Ollama connection errors**
   - Verify OLLAMA_HOST
   - Check if Ollama is running
   - Test with `curl http://localhost:11434/api/tags`

3. **Import errors**
   - Ensure virtual environment is activated
   - Reinstall dependencies: `pip install -r requirements.txt`

### Logs

```bash
# View application logs
tail -f /var/log/corefoundry/app.log

# View systemd logs
sudo journalctl -u corefoundry -f

# View Docker logs
docker-compose logs -f backend
```

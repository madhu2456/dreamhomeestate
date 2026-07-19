# Deployment — Dream Home Estate

Production domain: **https://dreamhomeestate.madhudadi.in**

## Architecture on the server

| Service | Role | Host exposure |
|---------|------|----------------|
| `web` | Next.js | `127.0.0.1:3010` |
| `api` | FastAPI | internal only |
| `worker` + `beat` | Celery publish jobs | internal |
| `postgres` / `redis` / `minio` | data | MinIO `127.0.0.1:9010` for `/media` |
| Host nginx | TLS + reverse proxy | 80/443 → app + media |

## One-time bootstrap (server, as root)

```bash
# Point DNS A record: dreamhomeestate.madhudadi.in → your server IP

export DEPLOY_USER=madhu
export DOMAIN=dreamhomeestate.madhudadi.in
export APP_DIR=/opt/dreamhomeestate
export REPO_URL=https://github.com/madhu2456/dreamhomeestate.git
export APP_PORT=3010
export MINIO_PORT=9010

git clone "$REPO_URL" "$APP_DIR"
cd "$APP_DIR"
chmod +x deploy.sh
sudo DOMAIN=$DOMAIN APP_DIR=$APP_DIR REPO_URL=$REPO_URL ./deploy.sh
```

This installs Docker (if needed), creates `.env`, builds `docker-compose.prod.yml`, runs migrations, and installs nginx.

### SSL

```bash
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d dreamhomeestate.madhudadi.in
```

After certs exist, the next `./deploy.sh --update` installs the SSL nginx template automatically.

### Create admin owner

```bash
cd /opt/dreamhomeestate
docker compose -f docker-compose.prod.yml exec api \
  python -m app.cli create-owner admin@dreamhomeestate.madhudadi.in "Admin" \
  --password 'choose-a-strong-password' \
  --org-name 'Dream Home Estate' \
  --org-slug dream-home-estate
```

Sign in at https://dreamhomeestate.madhudadi.in/login

## GitHub Actions CI/CD

Workflow: [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)

On every push to `main` (or manual **workflow_dispatch**), Actions SSHs as `madhu` and runs `./deploy.sh --update`.

### Required repository secrets

| Secret | Value |
|--------|--------|
| `DEPLOY_HOST` | Server IP or hostname |
| `DEPLOY_USER` | `madhu` |
| `DEPLOY_SSH_KEY` | Private key for `madhu` (full PEM) |

Optional: `DEPLOY_PORT` (default 22), `DEPLOY_PATH` (default `/opt/dreamhomeestate`), `DEPLOY_SSH_PASSPHRASE`

### Server prep for non-root deploys

```bash
# madhu must own the app tree and use Docker without root
usermod -aG docker madhu
chown -R madhu:madhu /opt/dreamhomeestate

# Optional: passwordless sudo for nginx install on each deploy
# (same pattern as deals.madhudadi.in)
```

Authorize the GitHub deploy key:

```bash
# On server as madhu
mkdir -p ~/.ssh && chmod 700 ~/.ssh
# Append the matching public key to ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

## Manual update

```bash
su - madhu
cd /opt/dreamhomeestate
./deploy.sh --update
```

## Useful commands

```bash
cd /opt/dreamhomeestate
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api web worker
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

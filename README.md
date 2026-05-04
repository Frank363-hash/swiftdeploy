# SwiftDeploy

A declarative deployment CLI tool that generates and manages a full containerised stack from a single `manifest.yaml` file.

## How It Works

`manifest.yaml` is the single source of truth. SwiftDeploy reads it and generates all configuration files, manages containers, and keeps your stack running. Nothing is handwritten the manifest drive everything.
manifest.yaml → swiftdeploy init → nginx.conf + docker-compose.yml → running stack
## Project Structure
swiftdeploy/
├── manifest.yaml              # Single source of truth
├── swiftdeploy                # CLI tool (bash)
├── Dockerfile                 # Builds the Python API image
├── README.md
├── app/
│   ├── main.py                # Python Flask API service
│   └── requirements.txt
└── templates/
├── nginx.conf.j2          # Nginx config template (Jinja2)
└── docker-compose.yml.j2  # Docker Compose template (Jinja2)

## prerequisites
- Docker
- Docker Compose
- Python 3
- curl

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/Frank363-hash/swiftdeploy.git
cd swiftdeploy
```

### 2. Make the CLI executable

```bash
chmod +x swiftdeploy
```

### 3. Build the Docker image

```bash
docker build -t swift-deploy-1-node:latest .
```

## Subcommand Walkthrough

### `init`
Parses `manifest.yaml` and generates `nginx.conf` and `docker-compose.yml` from Jinja2 templates.

```bash
./swiftdeploy init
```

Output:
[INFO] Running init — generating config files from manifest...
→ nginx.conf
→ docker-compose.yml
[PASS] Init complete.

### `validate`
Runs 5 pre-flight checks before deploying.

```bash
./swiftdeploy validate
```

Checks:
1. `manifest.yaml` exists and is valid YAML
2. All required fields are present and non-empty
3. Docker image exists locally
4. Nginx port is free on the host
5. Generated `nginx.conf` is syntactically valid

### `deploy`
Runs init, brings up the full stack, and waits until health checks pass (60s timeout).

```bash
./swiftdeploy deploy
```

Once deployed, access the service at: `http://localhost:8080`

### `promote`
Switches the deployment mode between `stable` and `canary`.

```bash
./swiftdeploy promote canary
./swiftdeploy promote stable
```

What it does:
- Updates `mode` in `manifest.yaml`
- Regenerates `docker-compose.yml` with the new `MODE` env var
- Restarts only the app container
- Confirms the new mode by hitting `/healthz`

### `teardown`
Stops and removes all containers, networks, and volumes.

```bash
# this one Stops and remove containers only
./swiftdeploy teardown

# Also delete generated config files
./swiftdeploy teardown --clean
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Welcome message with mode, version, timestamp |
| GET | `/healthz` | Liveness check with process uptime |
| POST | `/chaos` | Simulate degraded behaviour (canary only) |

### Chaos Modes (canary only)

```bash
# Slow mode — sleep N seconds before responding
curl -X POST http://localhost:8080/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "slow", "duration": 3}'

# Error mode — return 500 on ~50% of requests
curl -X POST http://localhost:8080/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "error", "rate": 0.5}'

# Recover — cancel all active chaos
curl -X POST http://localhost:8080/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "recover"}'
```

## Manifest Reference

```yaml
services:
  image: swift-deploy-1-node:latest   # Docker image name
  port: 3000                          # App internal port
  mode: stable                        # stable or canary
  version: "1.0.0"                    # App version
  restart_policy: unless-stopped      # Docker restart policy
  log_volume: app-logs                # Named volume for logs

nginx:
  image: nginx:latest                 # Nginx image
  port: 8080                          # Public port
  proxy_timeout: 30                   # Timeout in seconds

network:
  name: swiftdeploy-net               # Docker network name
  driver_type: bridge                 # Network driver
```

## Architecture
                ┌─────────────────┐
                User Traffic ───▶ │   Nginx :8080   │
│  (reverse proxy) │
└────────┬────────┘
│
┌────────▼────────┐
│   App :3000     │
│  (Flask API)    │
│  stable/canary  │
└─────────────────┘
     Both containers on swiftdeploy-net (bridge)
     App port never exposed directly to host.
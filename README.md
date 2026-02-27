# 🟢 Emerald Server Status Monitor

A lightweight, self-hosted wallboard that polls your **N-able RMM** instance and displays real-time server check-in status across all customers. Built with Python and plain HTML — no external dependencies beyond Docker.

---

## How It Works

A background Python thread authenticates with the N-able API every 5 minutes, fetches all managed devices, and flags any **Server-class device** that hasn't checked in within the configured threshold (default: **10 minutes**). 

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed
- An N-able RMM account with API access
- Your N-able **JWT API token** (generated from your N-able user profile)

---

## Quick Start

### 1. Download docker-compose.yml

Save the `docker-compose.yml` file to a folder on your host. No other files are needed — the image is pulled directly from Docker Hub.

```bash
# Or pull the image manually ahead of time
docker pull samuelstreets/nable-servers-offline-dashboard:latest
:latest
```

### 2. Set your API token

Open `docker-compose.yml` and replace the placeholder with your N-able JWT:

```yaml
environment:
  - NABLE_TOKEN=your_jwt_token_here
```

> ⚠️ **Never commit your JWT token to source control.**

### 3. Run

```bash
docker compose up -d
```

### 4. Open the wallboard

Navigate to [http://localhost:8080](http://localhost:8080) in your browser.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `NABLE_TOKEN` | *(required)* | Your N-able JWT API token |
| `PYTHONUNBUFFERED` | `1` | Ensures logs appear in real time |

The check-in threshold (`THRESHOLD_MINS`) defaults to **10 minutes** and can be changed in `app.py` before building a custom image.

---

## Severity Levels

| Colour | Severity | Condition |
|---|---|---|
| 🔴 Red | `critical` | Last seen < 24 hours ago but over threshold |
| 🟡 Yellow | `warning` | Last seen 1–7 days ago |
| ⚫ Grey | `stale` | Last seen > 7 days ago |
| 🟢 Green | — | All servers checked in within threshold |

---

## Stopping the Monitor

```bash
docker compose down
```

---

## Troubleshooting

**Wallboard shows "Awaiting Data..."**
The first harvest runs immediately on startup. Check container logs:
```bash
docker logs nable-monitor
```

**AUTH FAILED error in logs**
Your JWT token is invalid or expired. Regenerate it in N-able and update `docker-compose.yml`, then restart:
```bash
docker compose down && docker compose up -d
```

**No servers appearing**
Only devices with `deviceClass` containing `"Server"` and a `lastApplianceCheckinTime` value are displayed. Workstations and devices without a check-in timestamp are excluded by design.

**GitHub Actions build failing**
Check that both `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets are set correctly in your repo settings.

---

## Project Structure

| File | Purpose |
|---|---|
| `app.py` | Data harvester + embedded HTTP server |
| `index.html` | Wallboard frontend |
| `Dockerfile` | Container image definition |
| `docker-compose.yml` | Service orchestration (pull from Docker Hub) |
| `.github/workflows/docker-build.yml` | GitHub Actions CI/CD pipeline |

# 🟢 Emerald Server Status Monitor

A lightweight, self-hosted wallboard that polls your **N-able RMM** instance and displays real-time server check-in status across all customers. Built with Python and plain HTML — no external dependencies beyond Docker.

---

## How It Works

A background Python thread authenticates with the N-able API every **5 minutes**, fetches all managed devices, and flags any **Server-class device** that hasn't checked in within the configured threshold (default: **6 minutes**).

For recently offline servers (under 48 hours), the harvester also queries the **N-able Probe/Connectivity service** to distinguish between agent issues and genuine outages, refining the displayed label accordingly.

Results are sorted by severity weight so your most critical customers always appear first.

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

The wallboard auto-refreshes every **30 seconds**. The backend harvests fresh data every **5 minutes**.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `NABLE_TOKEN` | *(required)* | Your N-able JWT API token |
| `PYTHONUNBUFFERED` | `1` | Ensures logs appear in real time |

The check-in threshold (`THRESHOLD_MINS`) defaults to **6 minutes** and can be changed in `app.py` before building a custom image.

The N-able instance URL (`BASE_URL`) is also set in `app.py` — update this to match your own RMM instance.

---

## Severity Levels

Offline servers are classified into tiers based on how long ago they last checked in:

| Colour | Severity | Condition | Label |
|---|---|---|---|
| 🔴 Red | `critical` | Offline < 48 hours | 🚨 RECENTLY OFFLINE |
| 🔴 Red *(probe verified)* | `warning` | Offline < 48h, probe sees it online | 🛠️ FIX AGENT (Probe Verified) |
| 🔴 Red *(probe confirmed)* | `critical` | Offline < 48h, probe also failed | 🚨 CONFIRMED DOWN (Probe Failed) |
| 🟡 Yellow | `warning` | Offline 48 hours – 7 days | ⏳ STALE AGENT |
| ⚫ Grey | `stale` | Offline 7 – 14 days | 👻 LONG TERM OFFLINE |
| ⚫ Grey (dim) | `stale` | Offline > 14 days | 🕸️ HISTORICAL DOWN |
| 🟢 Green | — | All servers checked in within threshold | ✓ All systems active |

Customers are sorted by a weighted issue score so the most actionable problems appear at the top of the wallboard.

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
| `app.py` | Data harvester + probe interrogator + embedded HTTP server |
| `index.html` | Wallboard frontend (auto-refreshes every 30 seconds) |
| `Dockerfile` | Container image definition (Python 3.9 slim) |
| `docker-compose.yml` | Service orchestration (pulls from Docker Hub) |
| `.github/workflows/docker-build.yml` | GitHub Actions CI/CD — builds and pushes `linux/amd64` + `linux/arm64` images to Docker Hub on every push to `main` |

# Pixel 10 Autonomous Edge Node

A lightweight, Termux-based stack that turns a Pixel 10 into a self-managing edge
compute node with SSH access, LLM inference (Ollama), boot persistence, health
monitoring, and the groundwork for on-device UI automation via self-ADB.

## Architecture

```
┌─────────────────────────────────────────────┐
│  Pixel 10 (Android 16 / Termux)             │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │  sshd    │  │  crond   │  │  ollama   │ │
│  │  :8022   │  │ (15-min) │  │  :11434   │ │
│  └──────────┘  └──────────┘  └───────────┘ │
│       ▲             │              ▲        │
│       │        watchdog.sh         │        │
│       │        status-report.sh    │        │
│       │                            │        │
│  ┌────┴────────────────────────────┴──────┐ │
│  │  ~/.termux/boot/start-edge-node.sh     │ │
│  │  (runs on every device boot)           │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  ~/edge-node/                               │
│    ├── config/   node-identity.json         │
│    ├── logs/     boot-init.log, watchdog.log│
│    ├── data/     (app data, models)         │
│    └── scripts/  (user scripts)             │
└─────────────────────────────────────────────┘
         │
         │ SSH (port 8022)
         ▼
┌─────────────────────────────────────────────┐
│  GitHub Actions (deploy-pixel10.yml)        │
│  - Uploads scripts via scp                  │
│  - Runs bootstrap remotely                  │
│  - Captures output + fails on errors        │
│  - Uploads deploy logs as artifacts         │
└─────────────────────────────────────────────┘
```

## Quick Start (on-device)

```bash
# 1. Install Termux from F-Droid (not Play Store)
# 2. Open Termux and run:
pkg update -y && pkg install -y curl git
git clone https://github.com/Garrettc123/systems-master-hub.git
cd systems-master-hub

# 3. Bootstrap the edge node
bash termux/bootstrap.sh

# 4. (Optional) Install Termux:Boot from F-Droid, then:
#    Boot persistence is already configured by bootstrap.

# 5. (Optional) Set up self-ADB for UI automation
bash termux/self-adb-setup.sh
```

## Quick Start (remote via GitHub Actions)

1. Run `bash termux/bootstrap.sh` on the device once (or `deploy-pixel10-termux.sh`)
2. Copy the **private key** from `~/.ssh/pixel10_edge` to GitHub Secrets as `PIXEL10_SSH_KEY`
3. Go to **Actions > Deploy to Pixel 10** and trigger with `deploy_target: all`

## Scripts Reference

| Script | Location | Purpose |
|--------|----------|---------|
| `bootstrap.sh` | `termux/` | One-time idempotent setup: packages, SSH, dirs, identity |
| `boot-init.sh` | `termux/` | Termux:Boot auto-start: sshd, crond, Ollama, notification |
| `watchdog.sh` | `termux/` | Health check + auto-heal (cron every 15 min or manual) |
| `status-report.sh` | `termux/` | System snapshot (text or `--json` for CI parsing) |
| `self-adb-setup.sh` | `termux/` | Interactive ADB-over-WiFi pairing for on-device UI automation |
| `deploy-pixel10-termux.sh` | repo root | Original Termux setup (SSH + Ollama deploy prep) |

## Installed Packages

The bootstrap installs these Termux packages:

| Package | Why |
|---------|-----|
| `openssh` | Remote access via sshd on port 8022 |
| `termux-api` | Battery status, notifications, sensors, vibrate |
| `android-tools` | Self-ADB for UI automation (adb, input, screencap) |
| `python` | Scripting, lightweight ML, automation |
| `git` | Repository sync |
| `curl` | HTTP requests, health checks |
| `jq` | JSON parsing for API responses |
| `wget` | File downloads |
| `openssl` | TLS, certificate generation |
| `net-tools` | ifconfig, netstat |
| `iproute2` | ip command |
| `procps` | ps, top, free |
| `coreutils` | GNU standard utilities |
| `tar` | Archive handling |
| `cronie` | Cron daemon for scheduled tasks |
| `nano` | Quick on-device editing |

## Boot Persistence (Termux:Boot)

Install [Termux:Boot](https://f-droid.org/packages/com.termux.boot/) from F-Droid.
The bootstrap script creates `~/.termux/boot/start-edge-node.sh` which runs on
every device boot and starts:

1. **sshd** — remote access
2. **crond** — runs watchdog every 15 minutes
3. **Ollama** — LLM inference server (if installed)
4. **Android notification** — "Edge Node Online" with IP (via termux-api)

## Watchdog

The watchdog (`watchdog.sh`) runs every 15 minutes via cron and:

- Checks sshd, crond, and Ollama status
- Restarts any crashed service automatically
- Monitors disk space and battery level
- Sends Android notifications on critical issues
- Run `bash watchdog.sh --check` for read-only mode (no restarts)

## Self-ADB for UI Automation

Self-ADB lets Termux issue ADB commands (tap, swipe, screencap) without a
connected computer. This is the foundation for later UI automation.

### Setup

1. Enable **Developer Options** (Settings > About Phone > tap Build Number 7x)
2. Enable **USB Debugging** and **Wireless Debugging**
3. Run `bash termux/self-adb-setup.sh` and follow the prompts
4. After pairing, you can use `adb shell input tap X Y`, `adb shell screencap`, etc.

### Limitations

- Wireless Debugging must be re-enabled after each reboot
- The pairing code expires quickly — run the script promptly
- ADB is localhost-only (no network exposure)

## Status Report

```bash
# Text output (for humans)
bash status-report.sh

# JSON output (for CI/monitoring)
bash status-report.sh --json
```

The GitHub Actions workflow runs the status report after deployment and
includes the output in the workflow summary and artifacts.

## GitHub Actions Workflow

The `deploy-pixel10.yml` workflow supports:

| Target | What it does |
|--------|--------------|
| `bootstrap` | Uploads and runs bootstrap.sh + installs boot/watchdog scripts |
| `ollama` | Installs Ollama + pulls llama3.2:3b model |
| `health-check` | Runs remote status-report.sh |
| `all` | All of the above in sequence |

Key improvements over the original workflow:
- **Output capture**: All remote command output is logged and uploaded as artifacts
- **Fail-fast diagnostics**: Remote failures surface as GitHub Actions errors with log context
- **Modular targets**: Deploy just what you need instead of all-or-nothing
- **SSH keepalive**: Prevents timeout during long operations
- **Step summaries**: Rich markdown summaries with deploy logs

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
| `bootstrap.sh` | `termux/` | One-time idempotent setup: packages, SSH, dirs, identity, Slack env |
| `boot-init.sh` | `termux/` | Termux:Boot auto-start: sshd, crond, Ollama, notification |
| `watchdog.sh` | `termux/` | Health check + auto-heal + telemetry + Slack alerts (cron 15 min) |
| `status-report.sh` | `termux/` | System snapshot (text, `--json`, or `--slack` for Slack format) |
| `telemetry-collect.sh` | `termux/` | Termux:API telemetry: battery, WiFi, telephony, location, sensors |
| `slack-notify.sh` | `termux/` | Slack notification helper (webhook or bot token, self-DM default) |
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

## Telemetry Collection

The `telemetry-collect.sh` script gathers extended device telemetry via Termux:API
commands and outputs a compact JSON report. Each sensor is collected independently,
so missing permissions degrade gracefully (the field shows `"error":"denied_or_unavailable"`
instead of failing the entire report).

### Telemetry Signals

| Signal | Termux:API Command | Data Collected |
|--------|-------------------|----------------|
| Battery | `termux-battery-status` | percentage, status, temperature, plugged, health |
| WiFi | `termux-wifi-connectioninfo` | SSID, BSSID, RSSI, link speed, frequency, IP |
| Telephony | `termux-telephony-deviceinfo` | network type, data state, SIM state, phone type |
| Location | `termux-location` | lat/lon, altitude, accuracy, provider (network) |
| Sensors | `termux-sensor` | single snapshot from available hardware sensors |

### Usage

```bash
# Compact JSON (for piping to other tools)
bash termux/telemetry-collect.sh

# Pretty-printed JSON
bash termux/telemetry-collect.sh --pretty
```

The watchdog automatically runs telemetry collection every 15 minutes and saves
the latest snapshot to `~/edge-node/data/telemetry-latest.json`.

### Android Permissions Required

The following permissions must be granted to the **Termux:API** app (not Termux itself)
for telemetry to function. Grant them via Android Settings > Apps > Termux:API > Permissions:

| Permission | Required For | Impact if Denied |
|-----------|-------------|-----------------|
| **Location** | `termux-location` | Location field returns `"error":"denied_or_unavailable"` |
| **Phone** | `termux-telephony-deviceinfo` | Telephony field returns error |
| **Nearby devices / WiFi** | `termux-wifi-connectioninfo` | WiFi SSID may show `<unknown ssid>` |

Battery status and sensors typically work without extra permissions.

> **Tip**: Run `termux-battery-status` manually first. If Android shows a permission
> prompt, grant it. If nothing happens within 5 seconds, ensure the Termux:API app
> (separate from Termux) is installed from F-Droid.

## Slack Integration (RHNS Self-Reporting)

The edge node can report its status to Slack using the **self-DM command feed** pattern:
the default target is the current user's own Slack DM (user ID `U0A6G6YLRDK`), so
status messages appear as a private command log rather than cluttering team channels.

### How It Fits RHNS

The RHNS (Remote Health & Notification System) watchdog runs every 15 minutes via cron.
When it detects issues (service down, low battery, low disk), it:

1. Collects full telemetry via `telemetry-collect.sh`
2. Runs `status-report.sh --json` to build the system snapshot
3. Sends a Slack Block Kit message via `slack-notify.sh --status-report`
4. The message lands in your self-DM (or configured channel) with service status
   icons, battery level, disk usage, and network info

Healthy-state reports can be enabled by setting `SLACK_REPORT_ALWAYS=true`.

### Slack Setup

#### Option A: Incoming Webhook (Simplest)

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create an app (or use existing)
2. Enable **Incoming Webhooks** and add a webhook for your DM or a channel
3. Set the webhook URL on the device:
   ```bash
   # Edit the config file created by bootstrap:
   nano ~/edge-node/config/slack-env.sh
   # Uncomment and set:
   # export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T.../B.../xxx"
   ```

#### Option B: Bot Token

1. Create a Slack app with the `chat:write` scope
2. Install to workspace and copy the `xoxb-...` Bot User OAuth Token
3. Set on device:
   ```bash
   # Either as env var:
   export SLACK_BOT_TOKEN="xoxb-..."
   # Or write to a file (more secure):
   echo "xoxb-..." > ~/edge-node/config/.slack-token
   chmod 600 ~/edge-node/config/.slack-token
   export SLACK_TOKEN_FILE="$HOME/edge-node/config/.slack-token"
   ```

#### Option C: GitHub Actions Secret (for CI-triggered reports)

Add `SLACK_WEBHOOK` or `SLACK_BOT_TOKEN` as a GitHub repository secret.
The deploy workflow can pass it to the device via SSH environment.

### Configuration Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SLACK_CHANNEL_ID` | `U0A6G6YLRDK` | Target Slack channel or user ID (self-DM) |
| `SLACK_WEBHOOK_URL` | (none) | Incoming Webhook URL |
| `SLACK_BOT_TOKEN` | (none) | Bot User OAuth token (`xoxb-...`) |
| `SLACK_TOKEN_FILE` | (none) | Path to file containing bot token |
| `SLACK_REPORT_ALWAYS` | `false` | Send Slack reports even when healthy |
| `SLACK_DRY_RUN` | `false` | Print payload without sending |

### Secret Handling

**No raw secrets are stored in the repository.** The system is deployment-ready:

- `bootstrap.sh` creates a **template** config at `~/edge-node/config/slack-env.sh`
  with placeholders — the operator fills in the actual webhook/token on-device
- For file-based token storage, use `~/edge-node/config/.slack-token` with `chmod 600`
- For GitHub Actions, use repository secrets (`SLACK_WEBHOOK` or `SLACK_BOT_TOKEN`)
- The `slack-notify.sh` script checks for credentials at runtime and exits cleanly
  with an error message if none are configured

### Testing Slack Delivery

```bash
# Source your config
source ~/edge-node/config/slack-env.sh

# Dry run (prints payload, does not send)
SLACK_DRY_RUN=true bash termux/slack-notify.sh --status-report

# Send a test message
bash termux/slack-notify.sh "Hello from Pixel 10 edge node"

# Send full status report
bash termux/slack-notify.sh --status-report

# View Slack-formatted text output
bash termux/status-report.sh --slack
```

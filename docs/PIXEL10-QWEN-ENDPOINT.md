# Pixel 10 Edge Node — Qwen On-Device Inference Endpoint

This document describes how to pull, expose, and health-check a lightweight Qwen model on the Pixel 10 edge node using Ollama.

## Overview

| Field | Value |
|-------|-------|
| **Target model** | `qwen2.5:0.5b-instruct` |
| **Fallback model** | `qwen2.5:0.5b` |
| **Parameter count** | 0.5 billion |
| **Estimated disk** | ~400 MB |
| **Estimated RAM** | ~600 MB |
| **Inference host** | `http://127.0.0.1:11434` |

The Qwen 2.5 0.5B instruct variant is chosen as the first on-device inference model because it is small enough to run on the Pixel 10's Tensor G5 chip within Termux's memory budget, while still providing useful instruction-following capability.

## Prerequisites

1. **Ollama installed and healthy** — the existing deploy workflow handles this (`deploy-pixel10.yml` with `deploy_target=ollama`).
2. **At least 600 MB free disk** — the pull script checks this automatically.
3. **Termux bootstrap completed** — `bootstrap.sh` must have run at least once.

## Scripts

All scripts live in `termux/` and are designed to run on-device inside Termux.

### `qwen-model-pull.sh` — Download the model

Pulls the Qwen model into Ollama's local store. Tries the instruct variant first, falls back to the base variant if the pull fails.

```bash
# Default: qwen2.5:0.5b-instruct with qwen2.5:0.5b fallback
bash ~/qwen-model-pull.sh

# Override the target model
QWEN_MODEL="qwen2.5:0.5b" bash ~/qwen-model-pull.sh
```

**Outputs:** `~/edge-node/data/qwen-model-status.json`

### `qwen-endpoint-check.sh` — Validate the endpoint

Confirms the model is loaded, the API responds, and a smoke-test inference succeeds. Use this as a readiness gate before routing traffic.

```bash
bash ~/qwen-endpoint-check.sh          # human-readable
bash ~/qwen-endpoint-check.sh --json   # machine-readable JSON
```

**Exit codes:**
- `0` — healthy
- `1` — endpoint unreachable or model not loaded
- `2` — endpoint up but inference failed

**Outputs:** `~/edge-node/data/qwen-endpoint-status.json`

### `qwen-health-probe.sh` — Lightweight recurring probe

Designed for cron or watchdog integration. Runs three quick checks (Ollama alive, model present, inference responds) and writes a single-line JSON result.

```bash
bash ~/qwen-health-probe.sh             # human output
bash ~/qwen-health-probe.sh --json      # JSON to stdout
bash ~/qwen-health-probe.sh --quiet     # exit code only
```

**Outputs:** `~/edge-node/data/qwen-probe-latest.json`

Add to cron for continuous monitoring:

```bash
# Every 15 minutes
echo "*/15 * * * * bash ~/qwen-health-probe.sh --quiet >> ~/edge-node/logs/qwen-probe.log 2>&1" | crontab -
```

## Configuration

Model and endpoint settings are defined in `termux/qwen-model-config.json`. All scripts read from environment variables first, falling back to the defaults in this config:

| Variable | Default | Description |
|----------|---------|-------------|
| `QWEN_MODEL` | `qwen2.5:0.5b-instruct` | Primary model tag |
| `QWEN_FALLBACK_MODEL` | `qwen2.5:0.5b` | Fallback if primary fails |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama API base URL |
| `QWEN_PULL_TIMEOUT` | `900` | Max seconds for model pull |
| `QWEN_INFERENCE_TIMEOUT` | `30` | Max seconds for inference check |
| `QWEN_PROBE_TIMEOUT` | `15` | Max seconds for probe inference |

## Inference API

Once the model is pulled and Ollama is serving, use the standard Ollama API:

**Generate (single-turn):**

```bash
curl http://127.0.0.1:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen2.5:0.5b-instruct",
    "prompt": "Summarize edge computing in one sentence.",
    "stream": false
  }'
```

**Chat (multi-turn):**

```bash
curl http://127.0.0.1:11434/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen2.5:0.5b-instruct",
    "messages": [
      {"role": "user", "content": "What is edge AI?"}
    ],
    "stream": false
  }'
```

## GitHub Actions Integration

The `qwen-model-readiness.yml` workflow can be triggered manually to pull the Qwen model and verify the endpoint on the device. It runs after Ollama is confirmed healthy and uses the same SSH retry infrastructure as the main deploy workflow.

## Watchdog Integration

The existing `watchdog.sh` checks Ollama health. Once the Qwen model is deployed, `qwen-health-probe.sh` provides model-specific monitoring. To integrate:

```bash
# Add to watchdog.sh or run alongside it
if [ -f ~/qwen-health-probe.sh ]; then
  bash ~/qwen-health-probe.sh --quiet || echo "Qwen probe failed"
fi
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `ollama_unreachable` | Ollama not running | `ollama serve &` |
| `model_not_found` | Model not pulled yet | `bash qwen-model-pull.sh` |
| `inference_failed` | OOM or model loading | Check `free -m`, restart Ollama |
| `pull_failed` | Network or disk issue | Check connectivity and `df -h` |
| Slow first inference | Cold model load | Expected; subsequent calls are faster |

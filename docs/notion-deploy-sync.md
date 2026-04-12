# Notion Deployment Run Sync

Automatically writes each Pixel 10 deployment run into the **Deployment Runs** Notion database after every GitHub Actions run.

## Architecture

```
GitHub Actions (deploy workflow)
  └─ final step (if: always())
       └─ scripts/notify-notion-deploy.sh
            └─ Notion API (create or update page)
```

The sync script runs as the last step of every Pixel 10 deploy workflow. It uses `if: always()` so it executes even when earlier steps fail or are cancelled. It upserts pages keyed by **Run URL**, so re-running a workflow updates the existing record instead of creating duplicates.

## Required Repository Configuration

### Secrets

| Secret | Description | Example |
|--------|-------------|---------|
| `NOTION_API_KEY` | Notion internal integration token | `secret_abc123...` |

### Variables

| Variable | Description | Value |
|----------|-------------|-------|
| `NOTION_DEPLOY_DB_ID` | Notion database ID for Deployment Runs | `77d3f39f3631447eaefd748ee36ff75a` |

### Setup Steps

1. **Create a Notion internal integration:**
   - Go to https://www.notion.so/my-integrations
   - Click "New integration"
   - Name it (e.g., "GitHub Deploy Sync")
   - Select the workspace containing the Deployment Runs database
   - Copy the integration token (`secret_...`)

2. **Connect the integration to the database:**
   - Open the Deployment Runs database in Notion
   - Click the `...` menu in the top-right corner
   - Select "Connections" > "Connect to" > your integration name
   - Confirm access

3. **Add the GitHub secret and variable:**
   ```bash
   # Secret (sensitive — stored encrypted)
   gh secret set NOTION_API_KEY -R Garrettc123/systems-master-hub

   # Variable (non-sensitive — the database ID)
   gh variable set NOTION_DEPLOY_DB_ID \
     -R Garrettc123/systems-master-hub \
     --body "77d3f39f3631447eaefd748ee36ff75a"
   ```

## Database Properties

The script populates/updates these Notion database properties:

| Property | Type | Source |
|----------|------|--------|
| Run Name | Title | Workflow name + run number |
| Run URL | URL | `github.server_url/github.repository/actions/runs/github.run_id` |
| Run Status | Select | `job.status` mapped to Pass/Fail/Skipped |
| Run Started | Date | Workflow trigger timestamp |
| SSH | Select | `steps.check-ssh.outcome` |
| Pre-flight | Select | `steps.preflight.outcome` |
| Bootstrap | Select | `steps.bootstrap.outcome` |
| Watchdog | Select | `steps.watchdog.outcome` |
| Boot Persistence | Select | `steps.watchdog.outcome` |
| Ollama | Select | `steps.ollama.outcome` |
| RHNS Integration | Select | Hard-coded "Skipped" (not yet wired) |
| Health Check | Select | `steps.healthcheck.outcome` |
| Node IP | Rich Text | `github.event.inputs.device_ip` |
| Summary | Rich Text | Concatenated deploy context |

Step outcomes are mapped: `success` -> Pass, `failure` -> Fail, `cancelled`/`skipped` -> Skipped.

## Notion Database Setup

The database must have all the properties listed above with matching names and types. Select properties (Run Status, SSH, Pre-flight, etc.) need options: **Pass**, **Fail**, **Skipped**, **Unknown**.

Database URL: `https://www.notion.so/77d3f39f3631447eaefd748ee36ff75a`
Data source ID: `e50540f7-3c68-440d-9cd3-b387f6558f54`

## Upsert Behavior

The script queries the database for an existing page where `Run URL` matches the current run URL. If found, it updates that page. If not found, it creates a new page. This means:

- First run of a workflow: creates a new record
- Re-run of the same workflow: updates the existing record
- Different workflow runs: each gets its own record

## Failure Handling

The script exits `0` (non-fatal) if `NOTION_API_KEY` or `NOTION_DATABASE_ID` is not set, emitting a GitHub Actions error annotation. This ensures a missing secret never breaks an actual deployment.

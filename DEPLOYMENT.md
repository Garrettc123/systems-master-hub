# Full Stack Deployment Configuration
# Run: chmod +x scripts/deploy-full-stack.sh && ./scripts/deploy-full-stack.sh

## Environment Variables
AUTO_APPROVE=true
TF_ENV=prod
VERCEL_TOKEN=${VERCEL_TOKEN}
SLACK_WEBHOOK=${SLACK_WEBHOOK}
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}

## Deployment Phases
1. Workflows: Deploy universal CI/CD to 13 repositories
2. Terraform: Infrastructure as Code for dev/staging/prod
3. Vercel: Serverless functions (if token provided)
4. Slack: Notifications on success/failure

## Setup

### 1. Enable Script
```bash
chmod +x scripts/deploy-full-stack.sh
```

### 2. Set Environment Variables
```bash
export AUTO_APPROVE=true
export TF_ENV=prod
export VERCEL_TOKEN=your_vercel_token
export SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
```

### 3. Run Full Stack Deployment
```bash
./scripts/deploy-full-stack.sh
```

## What Gets Deployed
- ✅ 13 repositories (workflows)
- ✅ Terraform infrastructure
- ✅ Vercel serverless functions
- ✅ Slack notifications
- ✅ Timestamped logs

## Repos Included
1. nwu-protocol
2. autonomous-income-deployment
3. tree-of-life-system
4. enterprise-unified-platform
5. portfolio-website
6. ai-business-platform
7. APEX-Universal-AI-Operating-System
8. enterprise-mlops-platform
9. stablecoin-protocol
10. autohelix
11. systems-master-hub
12. quantum-advantage-layer
13. enterprise-automation-system

## Troubleshooting
- Check logs: `cat deployment_*.log`
- Terraform errors: `cd terraform && terraform validate`
- Vercel: Ensure token has deployment permissions
- Slack: Verify webhook URL is active

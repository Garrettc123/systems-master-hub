# 🚀 COMPLETE AUTO-DEPLOYMENT SETUP GUIDE
# All steps to fix AWS + GitHub + Git push

## STEP 1: Fix AWS IAM Permissions

### Option A: AWS Console (Fastest)
1. Go to: https://console.aws.amazon.com/iam/
2. Click: Users → Select your user
3. Click: Add inline policy
4. Paste this JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:AssumeRole",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "dynamodb:*",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "ec2:*",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "rds:*",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:*",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "cloudformation:*",
      "Resource": "*"
    }
  ]
}
```
5. Click: Create policy
6. Done! ✅

### Option B: AWS CLI (Command Line)
```bash
aws iam put-user-policy --user-name YOUR_USERNAME --policy-name TerraformPolicy --policy-document file://- << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "*", "Resource": "*"}
  ]
}
EOF
```

### Verify AWS Access
```bash
aws sts get-caller-identity
# Should output: UserId, Account, Arn
```

---

## STEP 2: Set GitHub Secrets (AWS Credentials)

### Get AWS Credentials
```bash
# Your AWS Access Key ID (from AWS Console or CLI)
echo $AWS_ACCESS_KEY_ID

# Your AWS Secret Access Key
echo $AWS_SECRET_ACCESS_KEY

# Get account ID
aws sts get-caller-identity --query Account --output text
```

### Set in GitHub (Easiest)
1. Go to: https://github.com/Garrettc123/systems-master-hub/settings/secrets/actions
2. Click: "New repository secret"
3. Add these secrets:

| Name | Value |
|------|-------|
| `prod_AWS_ACCESS_KEY_ID` | Your AWS Access Key |
| `prod_AWS_SECRET_ACCESS_KEY` | Your AWS Secret Key |
| `staging_AWS_ACCESS_KEY_ID` | Same (for now) |
| `staging_AWS_SECRET_ACCESS_KEY` | Same (for now) |
| `dev_AWS_ACCESS_KEY_ID` | Same (for now) |
| `dev_AWS_SECRET_ACCESS_KEY` | Same (for now) |
| `AWS_REGION` | `us-east-1` |
| `SLACK_WEBHOOK` | (Optional) Your Slack webhook |
| `VERCEL_TOKEN` | (Optional) Your Vercel token |
| `INFRACOST_API_KEY` | (Optional) Infracost API key |

### Set via GitHub CLI (Command Line)
```bash
gh secret set prod_AWS_ACCESS_KEY_ID -b "YOUR_AWS_ACCESS_KEY"
gh secret set prod_AWS_SECRET_ACCESS_KEY -b "YOUR_AWS_SECRET_KEY"
gh secret set staging_AWS_ACCESS_KEY_ID -b "YOUR_AWS_ACCESS_KEY"
gh secret set staging_AWS_SECRET_ACCESS_KEY -b "YOUR_AWS_SECRET_KEY"
gh secret set dev_AWS_ACCESS_KEY_ID -b "YOUR_AWS_ACCESS_KEY"
gh secret set dev_AWS_SECRET_ACCESS_KEY -b "YOUR_AWS_SECRET_KEY"
gh secret set AWS_REGION -b "us-east-1"
```

### Verify Secrets Set
```bash
gh secret list
```

---

## STEP 3: Fix Git & Push to Trigger Deployment

### Pull Latest Changes from Remote
```bash
cd systems-master-hub
git pull origin main --rebase
```

### If Conflicts (Rare)
```bash
# Accept remote changes
git checkout --theirs .
git add .
git rebase --continue
```

### Push to Trigger Auto-Deploy
```bash
git push origin main
```

### Verify Push Succeeded
```bash
git log --oneline -5
# Should show latest commits
```

---

## STEP 4: Monitor Deployment

### Watch Live in GitHub Actions
1. Go to: https://github.com/Garrettc123/systems-master-hub/actions
2. Click: "🚀 AUTO FULL STACK DEPLOY" workflow
3. Watch all 49 steps execute

### Check Logs
```bash
# List recent runs
gh run list

# View specific run
gh run view <RUN_ID>

# View logs
gh run view <RUN_ID> --log
```

### Slack Notifications
If webhook set, you'll get:
- ✅ Deployment success
- 🚨 Deployment failure
- 🔄 Auto-rollback alerts

---

## TROUBLESHOOTING

### "Still getting AWS error?"
```bash
# Verify credentials work
aws s3 ls
aws ec2 describe-instances

# If fails, recreate AWS credentials
aws iam create-access-key --user-name YOUR_USERNAME
```

### "Git push still fails?"
```bash
# Nuclear option (force push)
git push origin main --force
```

### "Workflow not starting?"
1. Check Actions tab is enabled: Settings > Actions > General
2. Check branch protection: Settings > Branches
3. Manually trigger: Actions > Full Stack Deploy > Run workflow

---

## QUICK COMMAND SUMMARY

```bash
# 1. Verify AWS
aws sts get-caller-identity

# 2. Pull latest
git pull origin main --rebase

# 3. Push to deploy
git push origin main

# 4. Monitor
gh run list
```

**That's it!** All 49 steps run automatically. ✅

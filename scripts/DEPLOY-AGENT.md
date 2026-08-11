# Production Deploy Agent

Pull-based CD for the production VM. You click **Run workflow** in GitHub; the VM
notices and deploys itself within ~2 minutes.

The VM never accepts inbound connections and no self-hosted runner is installed,
so a pull request from a fork can never execute anything here. This matters
because `iliyakarin/ikarin-bank` is a **public** repo.

## How it works

```
you: Actions -> "Deploy to Production" -> Run workflow
      |
      v
deploy.yml   checks docker-publish succeeded for this commit
      |      creates a GitHub Deployment (environment: production)
      v
GitHub Deployments API
      ^
      |      outbound HTTPS poll, every 2 min
karin-deploy-agent.timer -> .service -> karin-deploy-agent.sh
      |
      v
compose pull -> up -d -> alembic upgrade head -> prune -> health check
      |
      v
deployment status posted back: success / failure
```

A deployment that already has *any* status is treated as handled. That is the
idempotency guard that stops the timer from redeploying in a loop.

## One-time setup on the VM

Run these on `192.168.11.160` as `ikarin`.

### 1. Prerequisites

```bash
sudo apt-get update && sudo apt-get install -y curl jq
curl --version | head -1   # need >= 7.76 for --fail-with-body
```

### 2. GitHub token

Create a **fine-grained personal access token** at
<https://github.com/settings/personal-access-tokens/new>:

- Repository access: **Only select repositories** -> `iliyakarin/ikarin-bank`
- Repository permissions: **Deployments: Read and write** (nothing else)
- Expiration: set a calendar reminder to rotate it

Install it root-only:

```bash
sudo mkdir -p /etc/karin-deploy
printf '%s' 'github_pat_XXXXXXXXXXXX' | sudo tee /etc/karin-deploy/token >/dev/null
sudo chmod 600 /etc/karin-deploy/token
sudo chown root:root /etc/karin-deploy/token
```

This token is the only new secret. It cannot read code (the repo is public
anyway) and cannot write to the repository.

### 3. Confirm `.env.prod` is present

The agent deliberately never fetches `.env.prod` — it must already live on the
VM and stay out of git and CI:

```bash
ls -l /home/ikarin/karin-bank/.env.prod
```

If it is missing, copy it up once with the existing `deploy.sh` flow, then
never again.

### 4. Install the agent

```bash
REPO_TARBALL=https://github.com/iliyakarin/ikarin-bank/archive/main.tar.gz
curl -sSL "$REPO_TARBALL" | tar -xz --strip-components=2 -C /tmp \
  ikarin-bank-main/scripts/deploy-agent.sh \
  ikarin-bank-main/scripts/karin-deploy-agent.service \
  ikarin-bank-main/scripts/karin-deploy-agent.timer

sudo install -m 755 /tmp/deploy-agent.sh /usr/local/bin/karin-deploy-agent.sh
sudo install -m 644 /tmp/karin-deploy-agent.service /etc/systemd/system/
sudo install -m 644 /tmp/karin-deploy-agent.timer   /etc/systemd/system/
sudo systemctl daemon-reload
```

### 5. Dry run before enabling the timer

```bash
sudo /usr/local/bin/karin-deploy-agent.sh
```

With no pending deployment this should print `No deployments found` or
`already handled` and exit 0. That proves the token and network path work
without touching running services.

### 6. Enable

```bash
sudo systemctl enable --now karin-deploy-agent.timer
systemctl list-timers karin-deploy-agent.timer
```

## Deploying

1. Push to `main`; wait for **Build and Publish Docker Images** to go green.
2. Actions -> **Deploy to Production** -> *Run workflow*, optionally typing a reason.
3. Watch it land:

```bash
journalctl -u karin-deploy-agent -f
```

Status also appears in GitHub under the repo's Deployments/Environments view.

If images were never published for that commit, the workflow fails immediately
and no deployment is created — the VM stays untouched.

## Operations

```bash
# What happened last run?
journalctl -u karin-deploy-agent -n 100 --no-pager

# Deploy right now without waiting for the timer
sudo systemctl start karin-deploy-agent.service

# Pause automatic deploys
sudo systemctl disable --now karin-deploy-agent.timer
```

**Rollback:** the agent has no rollback of its own. Use the existing manual path
— `deploy.sh` remains fully functional as break-glass, and images are also
tagged `sha-<short>` in GHCR, so you can pin a known-good tag by hand.

## Known gaps

- `docker-compose.prod.yml` pins images to `:latest`, so the deployed image is
  whatever `latest` points to rather than the exact deployment SHA. Templating
  the tag as `${IMAGE_TAG}` and having the agent export the deployment SHA would
  close this.
- Migrations run with no automatic reversal. `alembic upgrade head` failing
  leaves the new containers up and reports `failure`; recovery is manual.
- The agent claims a deployment by posting `in_progress`. If it is killed
  mid-deploy, that deployment is not retried automatically.

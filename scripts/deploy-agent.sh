#!/usr/bin/env bash
#
# Pull-based production deploy agent for Karin Bank.
#
# Polls the GitHub Deployments API for a pending "production" deployment and
# applies it locally. Nothing is ever pushed into this VM: the agent only makes
# outbound HTTPS calls, so no inbound ports or self-hosted runner are needed.
#
# Deploy steps mirror deploy.sh, which stays as the manual break-glass path.
#
# Install: see scripts/DEPLOY-AGENT.md
set -euo pipefail

REPO="iliyakarin/ikarin-bank"
ENVIRONMENT="production"
DEPLOY_DIR="/home/ikarin/karin-bank"
TOKEN_FILE="/etc/karin-deploy/token"
HEALTH_URL="http://localhost/api/health"
HEALTH_RETRIES=12
HEALTH_DELAY=5

# Paths pulled from the repo at the deployed SHA. .env.prod is deliberately
# absent: it lives only on this VM and is never in git or in CI.
SYNCED_PATHS=("docker-compose.prod.yml" "nginx.prod.conf" "init-db")

COMPOSE=(docker compose --env-file .env.prod -f docker-compose.prod.yml)

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

if [ ! -r "$TOKEN_FILE" ]; then
    log "ERROR: token file $TOKEN_FILE is missing or unreadable"
    exit 1
fi
TOKEN="$(cat "$TOKEN_FILE")"

api() {
    curl -sS --fail-with-body \
        -H "Authorization: Bearer $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" "$@"
}

post_status() {
    local dep_id="$1" state="$2" desc="$3"
    api -X POST "https://api.github.com/repos/$REPO/deployments/$dep_id/statuses" \
        -d "{\"state\":\"$state\",\"description\":\"$desc\"}" >/dev/null
}

# --- 1. Find the newest production deployment -------------------------------
deployment="$(api "https://api.github.com/repos/$REPO/deployments?environment=$ENVIRONMENT&per_page=1")"
dep_id="$(jq -r '.[0].id // empty' <<<"$deployment")"
sha="$(jq -r '.[0].sha // empty' <<<"$deployment")"

if [ -z "$dep_id" ]; then
    log "No deployments found; nothing to do."
    exit 0
fi

# A deployment with any status has already been claimed by a previous run.
# This is the idempotency guard - it keeps the timer from redeploying forever.
existing_state="$(api "https://api.github.com/repos/$REPO/deployments/$dep_id/statuses?per_page=1" \
    | jq -r '.[0].state // empty')"
if [ -n "$existing_state" ]; then
    log "Deployment $dep_id already handled (state=$existing_state); nothing to do."
    exit 0
fi

log "Deployment $dep_id requested for ${sha:0:7}. Starting."
post_status "$dep_id" "in_progress" "Applying on VM"

# From here on, any failure must be reported back to GitHub.
trap 'post_status "$dep_id" "failure" "Deploy failed - see journalctl -u karin-deploy-agent" || true' ERR

# --- 2. Sync config from the repo at the deployed SHA ------------------------
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

log "Fetching repo tarball at $sha"
curl -sSL "https://github.com/$REPO/archive/$sha.tar.gz" | tar -xz -C "$workdir" --strip-components=1

mkdir -p "$DEPLOY_DIR"
for path in "${SYNCED_PATHS[@]}"; do
    if [ -e "$workdir/$path" ]; then
        log "Syncing $path"
        cp -r "$workdir/$path" "$DEPLOY_DIR/"
    else
        log "WARNING: $path not present at $sha, skipping"
    fi
done

cd "$DEPLOY_DIR"
if [ ! -f .env.prod ]; then
    log "ERROR: .env.prod missing in $DEPLOY_DIR - refusing to deploy"
    # Explicit: the ERR trap does not fire on a bare `exit`.
    post_status "$dep_id" "failure" ".env.prod missing on VM"
    exit 1
fi

# --- 3. Apply -----------------------------------------------------------------
log "Pulling images"
"${COMPOSE[@]}" pull

log "Restarting services"
"${COMPOSE[@]}" up -d --remove-orphans

log "Running database migrations"
"${COMPOSE[@]}" exec -T api alembic upgrade head

log "Pruning old images"
docker image prune -f

# --- 4. Verify ----------------------------------------------------------------
log "Waiting for health check"
for attempt in $(seq 1 "$HEALTH_RETRIES"); do
    if curl -sS --fail "$HEALTH_URL" >/dev/null 2>&1; then
        log "Healthy after ${attempt} attempt(s)."
        post_status "$dep_id" "success" "Deployed ${sha:0:7}"
        log "Deployment $dep_id complete."
        exit 0
    fi
    sleep "$HEALTH_DELAY"
done

log "ERROR: health check never passed at $HEALTH_URL"
# Explicit: the ERR trap does not fire on a bare `exit`.
post_status "$dep_id" "failure" "Health check failed after $((HEALTH_RETRIES * HEALTH_DELAY))s"
exit 1

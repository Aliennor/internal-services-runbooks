# Runbook: LiteLLM -> Langfuse Fix Deployment

Date: 2026-02-27  
Image (recommended slim): `docker.io/aliennor/redis-internal-services-langfuse-fix-slim@sha256:67106570636597f7e436028dd6722f091b369d9a9c9680a5c82e79ffb3c60c30`

## Goal
Apply only the LiteLLM/Langfuse wiring fix with minimal impact to the existing stack.

## 1) Pull image and extract to isolated staging folder
```bash
IMG="docker.io/aliennor/redis-internal-services-langfuse-fix-slim@sha256:67106570636597f7e436028dd6722f091b369d9a9c9680a5c82e79ffb3c60c30"
STAGE="/opt/orbina/internal_services_image_20260227"

docker pull "$IMG"
mkdir -p "$STAGE"
CID=$(docker create "$IMG")
docker cp "$CID":/etc/redis/internal_services/. "$STAGE"/
docker rm "$CID"
```

## 2) Backup current live LiteLLM files
```bash
LIVE="/opt/orbina/internal_services"
STAMP=$(date +%Y%m%d_%H%M%S)

cp "$LIVE/litellm/docker-compose.yml" "$LIVE/litellm/docker-compose.yml.bak_$STAMP"
cp "$LIVE/litellm/.env" "$LIVE/litellm/.env.bak_$STAMP"
```

## 3) Apply only the targeted fix files
```bash
cp "$STAGE/litellm/docker-compose.yml" "$LIVE/litellm/docker-compose.yml"
cp "$STAGE/litellm/.env" "$LIVE/litellm/.env"
```

## 4) Restart only Langfuse + LiteLLM
```bash
cd "$LIVE/langfuse" && docker compose up -d
cd "$LIVE/litellm" && docker compose up -d
```

## 5) Verify effective config and smoke test
```bash
# Should print langfuse-web:3000 values

docker exec litellm sh -lc 'echo "$LANGFUSE_BASE_URL | $LANGFUSE_HOST"'

# Send one LiteLLM request
curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer <LITELLM_MASTER_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-coder-30b","messages":[{"role":"user","content":"langfuse test ping"}]}'

# Check recent logs

docker logs --since 3m litellm | grep -Ei "langfuse|error|exception"
docker logs --since 3m langfuse-web | grep -Ei "ingest|trace|error|auth|401|403"
```

## 6) Rollback (if needed)
```bash
cp "$LIVE/litellm/docker-compose.yml.bak_$STAMP" "$LIVE/litellm/docker-compose.yml"
cp "$LIVE/litellm/.env.bak_$STAMP" "$LIVE/litellm/.env"
cd "$LIVE/litellm" && docker compose up -d
```

## Notes
- OpenWebUI host port remains `3000`.
- Langfuse host mapping is `5000:3000`; LiteLLM must use container-internal `http://langfuse-web:3000`.
- This slim image excludes `openweb-ui/nginx-logs` and other heavy/non-critical directories for faster deploy tests.

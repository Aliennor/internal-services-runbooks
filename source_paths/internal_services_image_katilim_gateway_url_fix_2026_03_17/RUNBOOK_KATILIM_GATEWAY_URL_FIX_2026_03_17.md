# Katilim Gateway URL Fix

Patch image:

- `aliennor/internal-services-katilim-gateway-url-fix-20260317:0.1.1`
- digest: `sha256:f5390cc3cfa5466d53796b6a6bf2410a1aae2a0e89c8cc9996af446e773c07b6`

Goal:

- switch Katilim LiteLLM model `api_base` URLs from the old technology gateway
  hosts to the Katilim gateway hosts
- update the Katilim LiteLLM `NO_PROXY` list to the same Katilim dev and prod
  gateway hosts

This patch touches only:

- `/opt/orbina/internal_services/litellm/litellm_config.yaml`
- `/opt/orbina/internal_services/litellm/docker-compose.yml`

It does not touch:

- secrets
- `.env` files
- nginx
- databases
- non-LiteLLM services

## 1. Back Up The Current LiteLLM Files

```bash
STAMP="$(date +%Y%m%d_%H%M%S)" && BACKUP_DIR="/opt/orbina/backups/katilim_gateway_url_fix_$STAMP" && sudo mkdir -p "$BACKUP_DIR"
```

```bash
sudo cp /opt/orbina/internal_services/litellm/litellm_config.yaml "$BACKUP_DIR/litellm_config.yaml"
```

```bash
sudo cp /opt/orbina/internal_services/litellm/docker-compose.yml "$BACKUP_DIR/docker-compose.yml"
```

```bash
cd "$BACKUP_DIR" && sha256sum litellm_config.yaml docker-compose.yml > SHA256SUMS.txt
```

## 2. Pull And Apply The Patch Image

```bash
docker pull aliennor/internal-services-katilim-gateway-url-fix-20260317:0.1.1
```

```bash
docker run --rm -v /opt/orbina:/output aliennor/internal-services-katilim-gateway-url-fix-20260317:0.1.1 /output
```

## 3. Validate The Patched Files Before Restart

```bash
rg -n 'ziraat-katilim-gateway|NO_PROXY|no_proxy' /opt/orbina/internal_services/litellm/litellm_config.yaml /opt/orbina/internal_services/litellm/docker-compose.yml
```

```bash
cd /opt/orbina/internal_services/litellm && docker compose config >/tmp/katilim_litellm_compose_config_20260317.txt
```

## 4. Restart Only LiteLLM

```bash
cd /opt/orbina/internal_services/litellm && docker compose up -d litellm
```

## 5. Smoke Checks

```bash
docker logs --since 2m litellm
```

```bash
curl -sS http://127.0.0.1:4000/health || true
```

```bash
curl -sS http://127.0.0.1:4000/v1/models -H 'Authorization: Bearer <LITELLM_MASTER_KEY>'
```

## 6. Rollback

Use the `BACKUP_DIR` printed in step `1`.

```bash
sudo cp "$BACKUP_DIR/litellm_config.yaml" /opt/orbina/internal_services/litellm/litellm_config.yaml
```

```bash
sudo cp "$BACKUP_DIR/docker-compose.yml" /opt/orbina/internal_services/litellm/docker-compose.yml
```

```bash
cd /opt/orbina/internal_services/litellm && docker compose up -d litellm
```

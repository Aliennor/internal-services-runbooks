# Katilim Dev VM LiteLLM Test Runbook

Use this on the dev VM itself after installation to test LiteLLM from the
server side.

Current dev targets:

- `VM1=10.210.22.88`
- `VM2=10.210.22.89`
- `DEV_LB_IP=10.210.22.164`

Current LiteLLM exposure in the stack:

- direct host port: `4000`
- nginx-routed hostname: `http://manavgat.yzyonetim-dev.ziraatkatilim.local`

Useful LiteLLM model names for dev validation:

- `gpt-oss-120b`
- `qwen3-coder-next`
- `bge-m3`
- `dots-ocr`
- `qwen3-vl`

You need the real LiteLLM bearer key from the active VM `.env` or the approved
secret source.

## 1. Set The LiteLLM Key In The Shell

```bash
export LITELLM_KEY="$(grep '^LITELLM_MASTER_KEY=' /opt/orbina/internal_services/litellm/.env | cut -d= -f2-)"
```

```bash
export LITELLM_LOCAL=http://127.0.0.1:4000
```

```bash
export LITELLM_HOSTNAME=http://manavgat.yzyonetim-dev.ziraatkatilim.local
```

## 2. Basic Service Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep litellm
```

```bash
ss -ltnp | grep ':4000'
```

```bash
docker logs --tail 100 litellm
```

## 3. Direct Local API Tests

```bash
curl -sS "$LITELLM_LOCAL/v1/models" -H "Authorization: Bearer $LITELLM_KEY"
```

```bash
curl -sS "$LITELLM_LOCAL/v1/models" -H "Authorization: Bearer $LITELLM_KEY" | grep -E 'gpt-oss-120b|qwen3-coder-next|bge-m3|dots-ocr|qwen3-vl'
```

```bash
curl -sS "$LITELLM_LOCAL/v1/chat/completions" -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"gpt-oss-120b","messages":[{"role":"user","content":"Reply with only: vm-dev-ok"}],"max_tokens":16}'
```

```bash
curl -sS "$LITELLM_LOCAL/v1/chat/completions" -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"qwen3-coder-next","messages":[{"role":"user","content":"Reply with only: coder-vm-dev-ok"}],"max_tokens":16}'
```

```bash
curl -sS "$LITELLM_LOCAL/v1/embeddings" -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"bge-m3","input":"Dev VM embedding test"}'
```

## 4. Test Through Nginx On The Same VM

```bash
curl -sS http://127.0.0.1/v1/models -H 'Host: manavgat.yzyonetim-dev.ziraatkatilim.local' -H "Authorization: Bearer $LITELLM_KEY"
```

```bash
curl -sS http://127.0.0.1/v1/chat/completions -H 'Host: manavgat.yzyonetim-dev.ziraatkatilim.local' -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"gpt-oss-120b","messages":[{"role":"user","content":"Reply with only: nginx-dev-ok"}],"max_tokens":16}'
```

## 5. Test Through The LB Path From The VM

```bash
curl -sS http://10.210.22.164/v1/models -H 'Host: manavgat.yzyonetim-dev.ziraatkatilim.local' -H "Authorization: Bearer $LITELLM_KEY"
```

## 6. Container-Internal Checks

```bash
docker exec -it litellm sh
```

Inside the container:

```bash
wget -qO- http://127.0.0.1:4000/v1/models
```

```bash
ls -l /app/litellm_config.yaml /app/custom_auth.py /app/custom_logging_callback.py
```

Exit:

```bash
exit
```

## 7. Troubleshooting Commands

```bash
curl -v "$LITELLM_LOCAL/v1/models" -H "Authorization: Bearer $LITELLM_KEY"
```

```bash
docker logs --tail 200 -f litellm
```

```bash
docker exec nginx-proxy sh -lc 'tail -n 100 /var/log/nginx/litellm_error.log 2>/dev/null || true'
```

## 8. Minimal Fast Test Set

```bash
export LITELLM_KEY="$(grep '^LITELLM_MASTER_KEY=' /opt/orbina/internal_services/litellm/.env | cut -d= -f2-)"
```

```bash
curl -sS http://127.0.0.1:4000/v1/models -H "Authorization: Bearer $LITELLM_KEY"
```

```bash
curl -sS http://127.0.0.1:4000/v1/chat/completions -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"gpt-oss-120b","messages":[{"role":"user","content":"Reply with only: ok"}],"max_tokens":16}'
```

```bash
curl -sS http://127.0.0.1:4000/v1/embeddings -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"bge-m3","input":"test"}'
```

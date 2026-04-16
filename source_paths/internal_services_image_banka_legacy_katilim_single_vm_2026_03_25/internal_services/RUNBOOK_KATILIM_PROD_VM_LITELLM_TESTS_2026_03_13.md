# Katilim Prod VM LiteLLM Test Runbook

Use this on the prod VM itself after installation to test LiteLLM from the
server side.

Current prod targets:

- `VM1=10.210.28.26`
- `VM2=10.210.28.27`
- `PROD_LB_IP=10.210.18.101`

Current LiteLLM exposure in the stack:

- direct host port: `4000`
- nginx-routed hostname: `http://manavgat.yzyonetim.ziraatkatilim.local`

Current useful LiteLLM model names:

- `gpt-oss-20b`
- `bge-m3`
- `jina-embed-v4`
- `dots-ocr`
- `qwen3-guard-4b`
- `qwen3-vl`
- `qwen3-8b-vl`

You need the real LiteLLM bearer key from the active VM `.env` or the approved
secret source.

## 1. Set The LiteLLM Key In The Shell

If you already know the key:

```bash
export LITELLM_KEY='PASTE_REAL_LITELLM_MASTER_KEY_HERE'
```

If you want to read it from the installed `.env` on the VM:

```bash
export LITELLM_KEY="$(grep '^LITELLM_MASTER_KEY=' /opt/orbina/internal_services/litellm/.env | cut -d= -f2-)"
```

Set common endpoints:

```bash
export LITELLM_LOCAL=http://127.0.0.1:4000
```

```bash
export LITELLM_HOSTNAME=http://manavgat.yzyonetim.ziraatkatilim.local
```

## 2. Basic Service Checks

Check the container is running:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep litellm
```

Check the port is listening locally:

```bash
ss -ltnp | grep ':4000'
```

Check container logs:

```bash
docker logs --tail 100 litellm
```

Check container health by direct HTTP:

```bash
curl -i "$LITELLM_LOCAL/v1/models" -H "Authorization: Bearer $LITELLM_KEY"
```

Expected result:

- HTTP `200`

## 3. Direct Local API Tests

List models:

```bash
curl -sS "$LITELLM_LOCAL/v1/models" -H "Authorization: Bearer $LITELLM_KEY"
```

Confirm expected prod models are present:

```bash
curl -sS "$LITELLM_LOCAL/v1/models" -H "Authorization: Bearer $LITELLM_KEY" | grep -E 'gpt-oss-20b|bge-m3|jina-embed-v4|qwen3-guard-4b|qwen3-vl'
```

Chat completion test:

```bash
curl -sS "$LITELLM_LOCAL/v1/chat/completions" -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"gpt-oss-20b","messages":[{"role":"user","content":"Reply with only: vm-ok"}],"max_tokens":16}'
```

Embedding test with `bge-m3`:

```bash
curl -sS "$LITELLM_LOCAL/v1/embeddings" -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"bge-m3","input":"Prod VM embedding test"}'
```

Embedding test with `jina-embed-v4`:

```bash
curl -sS "$LITELLM_LOCAL/v1/embeddings" -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"jina-embed-v4","input":"Prod VM jina embedding test"}'
```

Guard model test:

```bash
curl -sS "$LITELLM_LOCAL/v1/chat/completions" -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"qwen3-guard-4b","messages":[{"role":"user","content":"Reply with only: guard-vm-ok"}],"max_tokens":16}'
```

Vision-family text probe:

```bash
curl -sS "$LITELLM_LOCAL/v1/chat/completions" -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"qwen3-vl","messages":[{"role":"user","content":"Reply with only: vl-vm-ok"}],"max_tokens":16}'
```

OCR-family text probe:

```bash
curl -sS "$LITELLM_LOCAL/v1/chat/completions" -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"dots-ocr","messages":[{"role":"user","content":"Reply with only: ocr-vm-ok"}],"max_tokens":16}'
```

## 4. Test Through Nginx On The Same VM

If DNS is already working on the VM:

```bash
curl -sS "$LITELLM_HOSTNAME/v1/models" -H "Authorization: Bearer $LITELLM_KEY"
```

If DNS is not ready, force the Host header and route locally:

```bash
curl -sS http://127.0.0.1/v1/models -H 'Host: manavgat.yzyonetim.ziraatkatilim.local' -H "Authorization: Bearer $LITELLM_KEY"
```

Nginx-routed chat completion test:

```bash
curl -sS http://127.0.0.1/v1/chat/completions -H 'Host: manavgat.yzyonetim.ziraatkatilim.local' -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"gpt-oss-20b","messages":[{"role":"user","content":"Reply with only: nginx-ok"}],"max_tokens":16}'
```

## 5. Test Through The LB Path From The VM

This confirms routing beyond the raw local port:

```bash
curl -sS http://10.210.18.101/v1/models -H 'Host: manavgat.yzyonetim.ziraatkatilim.local' -H "Authorization: Bearer $LITELLM_KEY"
```

```bash
curl -sS http://10.210.18.101/v1/chat/completions -H 'Host: manavgat.yzyonetim.ziraatkatilim.local' -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"gpt-oss-20b","messages":[{"role":"user","content":"Reply with only: lb-vm-ok"}],"max_tokens":16}'
```

## 6. Upstream Reachability Checks

These confirm the VM can reach model upstreams, not just the LiteLLM process.

Check the prod gateway endpoint used by embeddings:

```bash
curl -kI --max-time 15 https://ziraat-technology-gateway.apps.prod.ai.zb/bge-m3/v1
```

Check the dev gateway endpoint used by some fallback models:

```bash
curl -kI --max-time 15 https://ziraat-technology-gateway.apps.dev.ai.zb/gpt-oss-120b/v1
```

Check the external qwen endpoint configured in LiteLLM:

```bash
curl -kI --max-time 15 https://modelqwenqwen3-coder-30b-a3b-instruct-proj-llm-models.apps.ztaka.core.ziraat.bank/v1
```

These do not need the LiteLLM key. They only confirm network reachability.

## 7. Container-Internal Checks

Open a shell in the LiteLLM container:

```bash
docker exec -it litellm sh
```

Inside the container, check local proxy reachability:

```bash
wget -qO- http://127.0.0.1:4000/v1/models
```

Inside the container, confirm config file presence:

```bash
ls -l /app/litellm_config.yaml /app/custom_auth.py /app/custom_logging_callback.py
```

Exit the container:

```bash
exit
```

## 8. Troubleshooting Commands

Verbose local models call:

```bash
curl -v "$LITELLM_LOCAL/v1/models" -H "Authorization: Bearer $LITELLM_KEY"
```

Verbose nginx-routed call:

```bash
curl -v http://127.0.0.1/v1/models -H 'Host: manavgat.yzyonetim.ziraatkatilim.local' -H "Authorization: Bearer $LITELLM_KEY"
```

Recent logs while invoking a test call:

```bash
docker logs --tail 200 -f litellm
```

Stop log following with `Ctrl+C`.

Check nginx side for LiteLLM errors:

```bash
docker exec nginx-proxy sh -lc 'tail -n 100 /var/log/nginx/litellm_error.log 2>/dev/null || true'
```

## 9. What Success Looks Like

Direct local success means:

- LiteLLM is listening on `127.0.0.1:4000`
- the bearer key is accepted
- `/v1/models` works
- at least one chat completion and one embedding call succeed

Nginx/LB success means:

- hostname routing is correct
- nginx reaches LiteLLM correctly
- the final production URL path works, not just the raw host port

## 10. What Failure Means

- `401` or `403`:
  - wrong LiteLLM key
- `404` through nginx/LB:
  - wrong hostname route or wrong Host header
- raw local tests work but LB tests fail:
  - LB or DNS path issue
- `/v1/models` works but model invocation fails:
  - upstream model gateway access or token problem
- direct local port fails:
  - LiteLLM container or host binding issue

## 11. Minimal Fast Test Set

If you only want the shortest useful VM-side checks, run these:

```bash
export LITELLM_KEY="$(grep '^LITELLM_MASTER_KEY=' /opt/orbina/internal_services/litellm/.env | cut -d= -f2-)"
```

```bash
curl -sS http://127.0.0.1:4000/v1/models -H "Authorization: Bearer $LITELLM_KEY"
```

```bash
curl -sS http://127.0.0.1:4000/v1/chat/completions -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"gpt-oss-20b","messages":[{"role":"user","content":"Reply with only: ok"}],"max_tokens":16}'
```

```bash
curl -sS http://127.0.0.1:4000/v1/embeddings -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" -d '{"model":"bge-m3","input":"test"}'
```

```bash
curl -sS http://127.0.0.1/v1/models -H 'Host: manavgat.yzyonetim.ziraatkatilim.local' -H "Authorization: Bearer $LITELLM_KEY"
```

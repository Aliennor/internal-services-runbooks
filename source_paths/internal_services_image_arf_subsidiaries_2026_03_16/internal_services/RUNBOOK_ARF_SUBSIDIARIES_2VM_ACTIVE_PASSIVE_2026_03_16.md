# ARF Subsidiaries 2VM Active-Passive Runbook

This derivative runbook keeps the Katilim operator flow but applies it to the
shared ARF platform for `ZFilo`, `ZPay`, and `ZYatirim`.

## Baseline

- `VM1` active
- `VM2` passive warm standby
- LB probes only `http://<vm>:18081/ready`
- `n8n`, `observability`, and optional `Ragflow/Qdrant` remain shared
  inherited services
- tenant endpoints are:
  - `openwebui-zfilo`
  - `openwebui-zpay`
  - `openwebui-zyatirim`
  - `llm-zfilo`
  - `llm-zpay`
  - `llm-zyatirim`
  - `langfuse-zfilo`
  - `langfuse-zpay`
  - `langfuse-zyatirim`

## Install Flow

1. Use the inherited scripts under `ops/install/katilim`.
2. Populate:
   - `shared-postgres/.env`
   - `litellm/.env`
   - `langfuse/.env`
   - other shared service `.env` files as required
3. Update the inventory file with:
   - VM IPs
   - LB IP
   - the real shared hostnames
   - the real tenant OpenWebUI, LiteLLM, and Langfuse hostnames
4. Bootstrap `VM1` first.
5. Run `smoke-test-active.sh` and confirm:
   - shared `openwebui.<domain>` compatibility route and shared n8n route
   - all 3 tenant OpenWebUI routes
   - all 3 LiteLLM routes
   - all 3 Langfuse routes
6. Bootstrap `VM2` as passive.
7. Enable passive sync from `VM1`.

## Required Env Themes

- `shared-postgres/.env` must create the 3 LiteLLM DBs and the 3 Langfuse DBs.
- `openweb-ui/.env` must provide the shared `WEBUI_SECRET_KEY` plus the three
  tenant `OPENAI_API_BASE_URL_*` and `WEBUI_NAME_*` values when defaults are
  not sufficient.
- `litellm/.env` must provide keys, passwords, and proxy base URLs for all
  three tenants.
- `langfuse/.env` must provide 3 Postgres URLs, 3 NextAuth URLs, 3 NextAuth
  secrets, shared ClickHouse/MinIO credentials, and the shared Redis password.

## Validation

- `curl http://openwebui.<domain>/`
- `curl http://openwebui-zfilo.<domain>/`
- `curl http://openwebui-zpay.<domain>/`
- `curl http://openwebui-zyatirim.<domain>/`
- `curl http://127.0.0.1:18081/status`
- `curl http://llm-zfilo.<domain>/health`
- `curl http://llm-zpay.<domain>/health`
- `curl http://llm-zyatirim.<domain>/health`
- `curl http://langfuse-zfilo.<domain>/`
- `curl http://langfuse-zpay.<domain>/`
- `curl http://langfuse-zyatirim.<domain>/`

## Failover

Promotion stays the same as Katilim:

```bash
cd /opt/orbina/internal_services
sudo ops/ha/promote-passive.sh
```

After promotion, move LB traffic to the promoted node and rerun the shared plus
tenant smoke checks.

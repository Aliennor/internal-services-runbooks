# Banka Langfuse ClickHouse Database Mismatch — Fresh Start

Applies to any Banka VM installed from r33 through r36 where `langfuse-web`
and/or `langfuse-worker` loop on:

```
ClickHouse traces table does not exist. Retrying in 10s...
```

or the `langfuse-worker` log shows `[Background Migration] Validation failed
for background migration 20241024_1730_migrate_traces_from_pg_to_ch`.

## Why

The Langfuse web entrypoint runs `/app/packages/shared/clickhouse/scripts/up.sh`
on startup to apply ClickHouse schema migrations. That script builds the
golang-migrate URL as

```
${CLICKHOUSE_MIGRATION_URL}?username=...&password=...&database=${CLICKHOUSE_DB}&...
```

If `CLICKHOUSE_DB` is unset (as it was in r33–r36), `up.sh` defaults it to
`default`. The `database=default` query param wins over the `/langfuse` path
that our compose pins into `CLICKHOUSE_MIGRATION_URL`, so every migration
silently ran against the `default` database. The app, meanwhile, queries
`http://clickhouse:8123/langfuse` — which is still empty — and loops forever.

A fresh reinstall by itself does **not** fix this: the wrong-DB migration
happens again on every boot. We must set `CLICKHOUSE_DB=langfuse` on the
langfuse containers so `up.sh` migrates into `langfuse`, and we must drop the
misplaced tables from `default` so golang-migrate re-applies cleanly.

## Fix On The Live Server

Run as root on the affected VM (dev108 / prod106 / prod107):

```bash
ts="$(date +%Y%m%d_%H%M%S)"
out="/root/banka-langfuse-ch-db-fresh-${ts}.log"
exec > >(tee -a "$out") 2>&1

base=/opt/orbina/internal_services
compose_file="$base/langfuse/docker-compose.yaml"
env_file="$base/langfuse/.env"

echo "== before env =="
grep -n 'CLICKHOUSE_DB\|CLICKHOUSE_MIGRATION_URL\|CLICKHOUSE_URL' "$env_file" || true

echo "== backup =="
cp -a "$compose_file" "${compose_file}.bak.${ts}"
cp -a "$env_file"     "${env_file}.bak.${ts}"

echo "== patch .env =="
if grep -q '^CLICKHOUSE_DB=' "$env_file"; then
  sed -i -E 's|^CLICKHOUSE_DB=.*|CLICKHOUSE_DB=langfuse|' "$env_file"
else
  echo 'CLICKHOUSE_DB=langfuse' >> "$env_file"
fi
grep -n '^CLICKHOUSE_DB=' "$env_file"

echo "== patch compose common env (only if not already there) =="
python3 - <<'PY'
import pathlib, re
p = pathlib.Path("/opt/orbina/internal_services/langfuse/docker-compose.yaml")
src = p.read_text()
if "CLICKHOUSE_DB: ${CLICKHOUSE_DB:-langfuse}" in src:
    print("compose already patched; skipping")
else:
    new = re.sub(
        r"(  CLICKHOUSE_CLUSTER_ENABLED: \$\{CLICKHOUSE_CLUSTER_ENABLED:-false\}\n)",
        r"\1  CLICKHOUSE_DB: ${CLICKHOUSE_DB:-langfuse}\n",
        src,
        count=1,
    )
    if new == src:
        print("WARNING: could not find CLICKHOUSE_CLUSTER_ENABLED anchor; add CLICKHOUSE_DB manually")
    else:
        p.write_text(new)
        print("compose patched")
PY

grep -n 'CLICKHOUSE_DB' "$compose_file" || true

echo "== stop langfuse-web and langfuse-worker =="
cd "$base/langfuse"
podman compose rm -f -s langfuse-web langfuse-worker || true

echo "== drop wrong-DB CH migration state so up.sh re-applies into langfuse =="
ch_pw="$(grep '^CLICKHOUSE_PASSWORD=' "$env_file" | cut -d= -f2-)"
ch_user="$(grep '^CLICKHOUSE_USER=' "$env_file" | cut -d= -f2- || true)"
ch_user="${ch_user:-clickhouse}"
cid="$(podman ps --format '{{.Names}}' | grep -E '^clickhouse$' | head -1)"
if [ -z "$cid" ]; then
  echo "clickhouse container not running; start the stack first"
  exit 1
fi

# show what is currently in default and langfuse DBs
podman exec "$cid" clickhouse-client --user "$ch_user" --password "$ch_pw" -q "
  SELECT database, name FROM system.tables
  WHERE database IN ('default','langfuse')
  ORDER BY database, name
" || true

# drop everything in default DB that Langfuse wrongly migrated there
podman exec "$cid" clickhouse-client --user "$ch_user" --password "$ch_pw" -q "
  DROP DATABASE IF EXISTS default SYNC;
  CREATE DATABASE default;
" || true

# make sure langfuse DB is fresh for a clean migrate (optional but safest)
podman exec "$cid" clickhouse-client --user "$ch_user" --password "$ch_pw" -q "
  DROP DATABASE IF EXISTS langfuse SYNC;
  CREATE DATABASE langfuse;
" || true

echo "== bring web + worker back up =="
podman compose up -d --force-recreate --no-deps langfuse-web langfuse-worker

echo "== wait for web to finish CH migrations (up to 240s) =="
for i in $(seq 1 48); do
  sleep 5
  if podman logs langfuse-web 2>&1 | grep -qE 'Starting HTTP server|"Server is ready"|listening on'; then
    echo "langfuse-web up after $((i*5))s"
    break
  fi
done

echo "== tables in langfuse DB =="
podman exec "$cid" clickhouse-client --user "$ch_user" --password "$ch_pw" -q "
  SELECT name FROM system.tables WHERE database='langfuse' ORDER BY name
"

echo "== worker log tail =="
podman logs --tail 60 langfuse-worker || true

echo "== web log tail =="
podman logs --tail 60 langfuse-web || true
```

## Pass Criteria

- The `SELECT name FROM system.tables WHERE database='langfuse'` query returns
  at least `traces`, `observations`, `scores`, `event_log`,
  `blob_storage_file_log`, plus the `schema_migrations` table.
- `podman logs langfuse-worker` no longer prints
  `ClickHouse traces table does not exist`.
- `podman logs langfuse-web` prints `Server is ready` / listening lines.
- The Langfuse UI at `https://langfuse.<banka-domain>` loads and accepts the
  default admin credentials from `.env`.

## Rollback

```bash
ts_backup="<timestamp you picked above>"
cp -a /opt/orbina/internal_services/langfuse/docker-compose.yaml.bak.${ts_backup} \
      /opt/orbina/internal_services/langfuse/docker-compose.yaml
cp -a /opt/orbina/internal_services/langfuse/.env.bak.${ts_backup} \
      /opt/orbina/internal_services/langfuse/.env
cd /opt/orbina/internal_services/langfuse
podman compose up -d --force-recreate --no-deps langfuse-web langfuse-worker
```

Rollback just reverts the env/compose; the CH tables will still be in
`langfuse` and empty, which is the same state an r35/r36 install lands in.

## Permanent Fix

Reinstall from
`docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-18-r37`
(or newer). r37 sets `CLICKHOUSE_DB=langfuse` in the compose common env and
in `.env`/`langfuse.env` for both direct-install and secure-config flows.

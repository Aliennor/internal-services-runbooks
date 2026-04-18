# Banka Dev108 Langfuse Init Admin And ClickHouse Race Fix

Target: `10.11.115.108` (Banka dev), existing r34 install.

## Symptoms

1. `podman logs --tail=160 langfuse-web` shows early in startup:

   ```text
   [Langfuse Init] LANGFUSE_INIT_ORG_ID is not set but other LANGFUSE_INIT_*
   variables are configured. The following variables will be ignored:
   LANGFUSE_INIT_ORG_NAME, LANGFUSE_INIT_PROJECT_NAME. Set LANGFUSE_INIT_ORG_ID
   to enable initialization.
   ```

   → no default admin / org / project is ever created, so first login at
   `https://mercek-yzyonetim.ziraat.bank/` fails.

2. Same log also shows repeated validation errors:

   ```text
   [Background Migration] Validation failed for background migration
   20241024_1730_migrate_traces_from_pg_to_ch: ClickHouse traces table does
   not exist
   ```

   → benign on a fresh install (those migrations only matter when upgrading
   from a pre-ClickHouse Langfuse), but the errors keep scaring operators.
   They occur because `langfuse-web` starts in parallel with
   `langfuse-worker` and runs the PG → CH background-migration validator
   before `langfuse-worker` finishes creating the ClickHouse tables.

## Root Cause In The Installer

- `langfuse/.env.example` and the encrypted config (`r7`) set
  `LANGFUSE_INIT_ORG_NAME` / `LANGFUSE_INIT_PROJECT_NAME` but not
  `LANGFUSE_INIT_ORG_ID`. Langfuse requires `*_ORG_ID` or the whole bundle
  is silently ignored.
- `langfuse/docker-compose.yaml` has `langfuse-web` depending only on
  `clickhouse` / `minio` / `redis` being healthy, not on `langfuse-worker`
  finishing its ClickHouse migrations.

Both are fixed in the installer source tree (see work log
`2026_04_18_*_banka_langfuse_init_admin_and_ch_race_fix.md`). The next
built installer image will carry the fix end-to-end. This check unblocks
the already-deployed `10.11.115.108` without waiting for that rebuild.

## Fix On The Live Dev Server

Run as root on `10.11.115.108`:

```bash
ts="$(date +%Y%m%d_%H%M%S)"
out="/root/banka-dev108-langfuse-init-fix-${ts}.log"
exec > >(tee -a "$out") 2>&1

base=/opt/orbina/internal_services
env_file="$base/langfuse/.env"
compose_file="$base/langfuse/docker-compose.yaml"

echo "== before =="
grep -E '^(LANGFUSE_INIT_|NEXTAUTH_URL=)' "$env_file" || true

cp -a "$env_file" "${env_file}.bak.${ts}"
cp -a "$compose_file" "${compose_file}.bak.${ts}"

upsert() {
  local f="$1" k="$2" v="$3"
  if grep -q "^${k}=" "$f"; then
    sed -i "s|^${k}=.*|${k}=${v}|" "$f"
  else
    printf '%s=%s\n' "$k" "$v" >> "$f"
  fi
}

upsert "$env_file" LANGFUSE_INIT_ORG_ID        "banka-dev-org"
upsert "$env_file" LANGFUSE_INIT_ORG_NAME      "Banka Dev"
upsert "$env_file" LANGFUSE_INIT_PROJECT_ID    "banka-dev-project"
upsert "$env_file" LANGFUSE_INIT_PROJECT_NAME  "Banka Dev"
upsert "$env_file" LANGFUSE_INIT_USER_EMAIL    "admin@banka.local"
upsert "$env_file" LANGFUSE_INIT_USER_NAME     "Banka Dev Admin"
upsert "$env_file" LANGFUSE_INIT_USER_PASSWORD "ChangeMeBankaDev2026!"

echo "== after =="
grep -E '^(LANGFUSE_INIT_|NEXTAUTH_URL=)' "$env_file"

echo "== recreate langfuse-web so new env is applied =="
cd "$base/langfuse"
podman compose up -d --force-recreate --no-deps langfuse-web

echo "== wait for :3000 to be ready =="
for i in $(seq 1 60); do
  if curl -fsS --max-time 3 http://127.0.0.1:3000/api/public/health >/dev/null; then
    echo "langfuse-web ready (iter=$i)"
    break
  fi
  sleep 2
done

echo "== confirm init scripts ran =="
podman logs --tail=200 langfuse-web 2>&1 | \
  grep -E 'Langfuse Init|default (organization|project|user)|auto-created' || true

echo "log=$out"
```

Notes:

- The operator should rotate the password immediately after first login.
- If the worker is still reporting ClickHouse migrations in flight at the
  time `langfuse-web` recreates, the init scripts will block on
  `ClickHouse traces table does not exist` for 30–40 s and then proceed;
  this is expected on an existing deployment where we did not add the
  `depends_on: langfuse-worker` gate (that lands in the next rebuild).

## Validate

From a browser that can reach the dev VM:

1. Open `https://mercek-yzyonetim.ziraat.bank/`.
2. Log in as `admin@banka.local` / `ChangeMeBankaDev2026!`.
3. Expect to land in the `Banka Dev` org / `Banka Dev` project.
4. Change the password under the user settings page.

If login still fails:

- Re-check `podman logs langfuse-web` for the `Langfuse Init` banner.
- If it still says `LANGFUSE_INIT_ORG_ID is not set`, the container did
  not pick up the new env. Repeat `podman compose up -d --force-recreate
  --no-deps langfuse-web` from `$base/langfuse`.

## Send Back

- `/root/banka-dev108-langfuse-init-fix-*.log`
- Whether login succeeded, and whether you see the `Banka Dev` org on the
  landing page.

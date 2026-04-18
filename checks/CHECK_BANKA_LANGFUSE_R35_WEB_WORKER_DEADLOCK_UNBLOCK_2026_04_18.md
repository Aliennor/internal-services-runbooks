# Banka Langfuse r35 Web/Worker Startup Deadlock Unblock

Target: Any Banka VM that has already extracted the `r35` install bundle
(`docker.io/aliennor/internal-services-katilim-install:banka-langfuse-2026-04-18-r35`)
and is now stuck during first boot of Langfuse.

If the VM has not yet been installed, use `r36` from the install
runbooks instead — the deadlock is fixed there and no manual work is
needed. This check is only for operators who already rolled `r35`.

## Symptoms

1. `podman logs langfuse-worker` shows a burst of Prisma errors right
   after `Listening: http://<id>:3030`:

   ```text
   Raw query failed. Code: `42P01`.
   Message: `relation "models" does not exist`
   ...
   The table `public.background_migrations` does not exist in the current database.
   The table `public.eval_templates` does not exist in the current database.
   The table `public.dashboard_widgets` does not exist in the current database.
   ```

2. `podman ps --format '{{.Names}} {{.Status}}' | grep langfuse-web`
   reports `Up ... (created)` or `Waiting` and never reaches
   `healthy` / `running`.

3. `install-node.sh` (or any operator bootstrap loop) hangs at the
   Langfuse readiness wait because `langfuse-web` is blocked behind
   `langfuse-worker: service_healthy`.

## Root Cause

In the `r35` bundle, `internal_services/langfuse/docker-compose.yaml`
adds:

```yaml
langfuse-web:
  depends_on:
    langfuse-worker:
      condition: service_healthy
```

However, **only `langfuse-web` runs the Prisma (Postgres) migrations on
startup**. `langfuse-worker` does *not* create the `models`,
`background_migrations`, `eval_templates`, or `dashboard_widgets`
tables; it only runs ClickHouse migrations. Gating web on worker
produces a perfect chicken-and-egg:

- Worker starts, queries Postgres → tables missing → healthcheck
  never flips to healthy.
- Web waits for worker → web never runs → tables are never created.
- Install hangs indefinitely.

The fix in the installer source tree (landing as `r36`) removes the
`langfuse-worker: service_healthy` dependency and keeps the worker
healthcheck only for diagnostics. This check applies the same change
to an already-deployed `r35` tree without waiting for the rebuild.

## Fix On The Live Server

Run as root on the affected VM:

```bash
ts="$(date +%Y%m%d_%H%M%S)"
out="/root/banka-langfuse-r35-deadlock-unblock-${ts}.log"
exec > >(tee -a "$out") 2>&1

base=/opt/orbina/internal_services
compose_file="$base/langfuse/docker-compose.yaml"

echo "== before =="
grep -n -A 2 -B 1 'langfuse-worker:' "$compose_file" | sed -n '1,80p'

cp -a "$compose_file" "${compose_file}.bak.${ts}"

python3 - <<'PY'
import io, re, pathlib
p = pathlib.Path("/opt/orbina/internal_services/langfuse/docker-compose.yaml")
src = p.read_text()

pattern = re.compile(
    r"    depends_on:\n"
    r"      langfuse-worker:\n"
    r"        condition: service_healthy\n"
)
new = pattern.sub("    depends_on:\n", src, count=1)

if new == src:
    print("no deadlock block matched; file may already be fixed")
else:
    p.write_text(new)
    print("deadlock dependency removed")
PY

echo "== after =="
grep -n -A 2 -B 1 'langfuse-worker:' "$compose_file" | sed -n '1,80p'

echo "== force-recreate langfuse-web and langfuse-worker =="
cd "$base/langfuse"
podman compose up -d --force-recreate --no-deps langfuse-web langfuse-worker

echo "== wait for postgres tables via worker logs to go quiet =="
for i in $(seq 1 60); do
  if ! podman logs --tail=30 langfuse-worker 2>&1 | \
       grep -q 'relation "models" does not exist\|background_migrations. does not exist'; then
    echo "worker is no longer reporting missing tables (iter=$i)"
    break
  fi
  sleep 5
done

echo "== wait for langfuse-web on :3000 =="
for i in $(seq 1 60); do
  if curl -fsS --max-time 3 http://127.0.0.1:3000/api/public/health >/dev/null; then
    echo "langfuse-web ready (iter=$i)"
    break
  fi
  sleep 2
done

echo "== confirm init scripts ran =="
podman logs --tail=400 langfuse-web 2>&1 | \
  grep -E 'Langfuse Init|default (organization|project|user)|auto-created' || true

echo "== sanity =="
podman ps --format '{{.Names}} {{.Status}}' | grep ^langfuse

echo "log=$out"
```

## Validate

From a browser that can reach the VM:

1. Open the Langfuse public URL (`https://mercek-yzyonetim.ziraat.bank`
   for prod, `https://mercek-yzyonetim-dev.ziraat.bank` for dev108).
2. Log in with the inventory `LANGFUSE_INIT_USER_EMAIL` /
   `LANGFUSE_INIT_USER_PASSWORD` (default
   `admin@banka.local` / `ChangeMeBanka2026!` for prod; dev uses
   `ChangeMeBankaDev2026!`).
3. Expect to land in the default org / project.
4. Rotate the admin password immediately.

If login still fails:

- Re-check `podman logs langfuse-web` for the `Langfuse Init` banner;
  if it reports `LANGFUSE_INIT_ORG_ID is not set`, also apply
  `CHECK_BANKA_DEV108_LANGFUSE_INIT_ADMIN_AND_CH_RACE_2026_04_18.md`.

## Send Back

- `/root/banka-langfuse-r35-deadlock-unblock-*.log`
- Output of `podman ps --format '{{.Names}} {{.Status}}' | grep ^langfuse`.
- Confirmation that login succeeded.

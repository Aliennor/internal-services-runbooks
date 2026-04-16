# ARF Subsidiary Final Shared-Backend Bundle Runbook

Date:

- `2026-04-06`

Patch image tag:

- current:
  `docker.io/aliennor/internal-services-arf-subsidiary-final-shared-backend-bundle-20260406:0.1.1`
- previous:
  `docker.io/aliennor/internal-services-arf-subsidiary-final-shared-backend-bundle-20260406:0.1.0`

## Goal

Pull one Docker image on the company server and extract:

- the authoritative April 6 final shared-backend architecture/doc pack
- the current operational system docs/scripts
- the new `ops/install/subsidiary-shared-backend` installer bundle

## Scope

This bundle is documentation + installer payload.

It does not:

- modify secrets
- restart running services automatically
- overwrite the server tree unless you run the optional apply step

## Build And Push

This bundle is intended to be built from:

- `/Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_arf_subsidiary_final_shared_backend_bundle_2026_04_06`

Reference build/push commands:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_arf_subsidiary_final_shared_backend_bundle_2026_04_06
docker buildx build --platform linux/amd64 -t docker.io/aliennor/internal-services-arf-subsidiary-final-shared-backend-bundle-20260406:0.1.1 --load .
docker push docker.io/aliennor/internal-services-arf-subsidiary-final-shared-backend-bundle-20260406:0.1.1
```

## Pull And Extract On Server

```bash
IMAGE=docker.io/aliennor/internal-services-arf-subsidiary-final-shared-backend-bundle-20260406:0.1.1
STAMP=$(date +%Y%m%d_%H%M%S)
BASE=/opt/orbina/doc_bundles/arf_subsidiary_final_shared_backend_bundle_${STAMP}

docker pull "${IMAGE}"
CID=$(docker create "${IMAGE}" true)
mkdir -p "${BASE}"
docker cp "${CID}:/payload/." "${BASE}/"
docker rm "${CID}"

cd "${BASE}"
find . -type f | sort > FILELIST.txt
find . -type f -print0 | xargs -0 shasum -a 256 > SHA256SUMS.txt
```

## Expected Extracted Layout

```text
${BASE}/
  BUNDLE_CONTENTS.md
  RUNBOOK_ARF_SUBSIDIARY_FINAL_SHARED_BACKEND_BUNDLE_2026_04_06.md
  current_operational_system/internal_services/...
  final_architecture/subsidiary-3x-shared-backend-final-2026-04-06/...
  notes/2026_04_06_1516_arf_subsidiary_final_shared_backend_installer_impl.md
```

## Review Before Any Apply

```bash
cd "${BASE}"
sed -n '1,200p' BUNDLE_CONTENTS.md
sed -n '1,240p' notes/2026_04_06_1516_arf_subsidiary_final_shared_backend_installer_impl.md
find final_architecture/subsidiary-3x-shared-backend-final-2026-04-06 -maxdepth 1 -type f | sort
find current_operational_system/internal_services/ops/install/subsidiary-shared-backend -maxdepth 2 -type f | sort
```

## Optional Apply To Existing Server Tree

Use this only if the server already has an `internal_services` tree and you want
to place the new installer/docs into it for operator use.

```bash
STAMP=$(date +%Y%m%d_%H%M%S)
BASE=$(ls -dt /opt/orbina/doc_bundles/arf_subsidiary_final_shared_backend_bundle_* | head -n 1)
TARGET_ROOT=/opt/orbina/internal_services
BACKUP=/opt/orbina/backups/arf_subsidiary_final_shared_backend_bundle_${STAMP}

mkdir -p "${BACKUP}"
mkdir -p "${BACKUP}/ops/install" "${BACKUP}/ops"

cp -p "${TARGET_ROOT}/README.md" "${BACKUP}/README.md"
cp -R "${TARGET_ROOT}/ops/install/katilim" "${BACKUP}/ops/install/"
cp -R "${TARGET_ROOT}/ops/ha" "${BACKUP}/ops/"
if [ -d "${TARGET_ROOT}/ops/install/subsidiary-shared-backend" ]; then
  cp -R "${TARGET_ROOT}/ops/install/subsidiary-shared-backend" "${BACKUP}/ops/install/"
fi

cp -p "${BASE}/current_operational_system/internal_services/README.md" "${TARGET_ROOT}/README.md"

mkdir -p "${TARGET_ROOT}/ops/install/katilim"
cp -R "${BASE}/current_operational_system/internal_services/ops/install/katilim/." "${TARGET_ROOT}/ops/install/katilim/"

mkdir -p "${TARGET_ROOT}/ops/ha"
cp -R "${BASE}/current_operational_system/internal_services/ops/ha/." "${TARGET_ROOT}/ops/ha/"

mkdir -p "${TARGET_ROOT}/ops/install/subsidiary-shared-backend"
cp -R "${BASE}/current_operational_system/internal_services/ops/install/subsidiary-shared-backend/." "${TARGET_ROOT}/ops/install/subsidiary-shared-backend/"
```

## Post-Apply Validation

These checks are safe and targeted. They do not restart services.

```bash
cd /opt/orbina/internal_services

bash -n ops/install/subsidiary-shared-backend/lib.sh
bash -n ops/install/subsidiary-shared-backend/render-config.sh
bash -n ops/install/subsidiary-shared-backend/apply-bootstrap-contracts.sh
bash -n ops/install/subsidiary-shared-backend/bootstrap-vm1-active.sh
bash -n ops/install/subsidiary-shared-backend/bootstrap-vm2-standby.sh
bash -n ops/install/subsidiary-shared-backend/promote-vm2-n8n.sh
bash -n ops/install/subsidiary-shared-backend/smoke-test-app-node.sh
bash -n ops/install/subsidiary-shared-backend/validate-rendered-config.sh

./ops/install/subsidiary-shared-backend/render-config.sh ./ops/install/subsidiary-shared-backend/inventory.env.example
./ops/install/subsidiary-shared-backend/validate-rendered-config.sh ./ops/install/subsidiary-shared-backend/inventory.env.example
```

## Optional Runtime Follow-Up

Do this only on the real target environment after inventory values are replaced
with real endpoints and credentials:

```bash
cd /opt/orbina/internal_services
./ops/install/subsidiary-shared-backend/apply-bootstrap-contracts.sh --inventory ./ops/install/subsidiary-shared-backend/inventory.env --render-only
```

Real runtime checks still needed later:

- `OpenWebUI` PostgreSQL + MinIO attachment flow
- `n8n` `VM1` active / `VM2` standby promotion
- Redis failover behind the real service endpoint
- shared MySQL, ClickHouse, MinIO, and Elasticsearch health
- `RAGFlow` MySQL/Redis/MinIO/Elasticsearch tenant isolation

## Rollback

If you ran the optional apply step and want to revert the copied docs/scripts:

```bash
BACKUP=$(ls -dt /opt/orbina/backups/arf_subsidiary_final_shared_backend_bundle_* | head -n 1)
TARGET_ROOT=/opt/orbina/internal_services

cp -p "${BACKUP}/README.md" "${TARGET_ROOT}/README.md"
rm -rf "${TARGET_ROOT}/ops/install/katilim"
cp -R "${BACKUP}/ops/install/katilim" "${TARGET_ROOT}/ops/install/"
rm -rf "${TARGET_ROOT}/ops/ha"
cp -R "${BACKUP}/ops/ha" "${TARGET_ROOT}/ops/"

if [ -d "${BACKUP}/ops/install/subsidiary-shared-backend" ]; then
  rm -rf "${TARGET_ROOT}/ops/install/subsidiary-shared-backend"
  cp -R "${BACKUP}/ops/install/subsidiary-shared-backend" "${TARGET_ROOT}/ops/install/"
fi
```

## Notes

- This package intentionally keeps both systems visible:
  - historical Katilim-derived operational flow
  - final shared-backend installer flow
- The authoritative architecture pack is included separately so the server has
  both the design authority and the operational installer bundle in one pull.

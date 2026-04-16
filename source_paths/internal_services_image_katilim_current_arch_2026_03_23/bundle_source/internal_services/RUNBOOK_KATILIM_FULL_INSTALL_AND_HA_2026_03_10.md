# Katilim Full Install And HA Runbook

Use this as the single operator runbook for the Katilim 2-VM installation.

For LB key and CSR generation, use:

- `RUNBOOK_KATILIM_LB_CERTIFICATES_AND_CSRS_2026_03_12.md`

For Windows-side dev LiteLLM reachability and API tests, use:

- `RUNBOOK_KATILIM_DEV_WINDOWS_LITELLM_TESTS_2026_03_13.md`

For VM-side dev LiteLLM validation on the installed servers, use:

- `RUNBOOK_KATILIM_DEV_VM_LITELLM_TESTS_2026_03_13.md`

For the HA sync staging retention fix on already-installed Katilim nodes, use:

- `RUNBOOK_KATILIM_HA_SYNC_STAGING_RETENTION_FIX_2026_03_16.md`

It covers:

- workstation preparation
- Nexus behavior and Docker configuration
- delivery of the install tree to both VMs
- `VM1` first bring-up
- optional Ragflow volume restore
- `VM2` passive standby bootstrap
- sync enablement
- validation
- promotion and fallback

Scope:

- baseline snapshot: March 9 exported working server
- install root on the VMs: `/opt/orbina/internal_services`
- topology: `VM1` active, `VM2` passive warm standby
- first goal: get `VM1` serving successfully
- second goal: add `VM2` as passive HA standby

## Quick Path

Use this exact path for the current Katilim installation.

Use the `r17` install image tag and the current config image tags in this
runbook. The earlier
`katilim-2vm-2026-03-10` pull images had a broken Alpine `bash` entrypoint,
the `r2` install bundle still had a broken registry-check `awk` command, and
the `r3` install bundle still passed `--litellm-image-tar` even when empty.
The `r4` bundle is superseded by the corrected LiteLLM source mapping. The
`r5` install bundle still let `bootstrap-vm1-active.sh` fail too early while
the stack was warming up. The `r6` bundle still had a false-negative active
health probe for nginx. The `r7` bundle predates the prod hostname/inventory
rendering additions. The `r8` bundle predates image-based Ragflow export
restore support. The `r9` install bundle still left Ragflow MinIO on a direct
`quay.io` image instead of the mirrored `aliennor/ragflow-minio` tag. The
`r10` bundle predates the corrected amd64 Ragflow MinIO mirror and the
default Ragflow port move from `5000/5001` to `5100/5101`. The `r11` bundle
still relied on the mutable `aliennor/ragflow-minio:RELEASE...` tag, which
can stay stale behind Nexus. The `r12` bundle pins Ragflow MinIO by digest to
avoid that cache problem. The `r16` bundle moves Ragflow web/admin host
ports off the conflicting `8000/8001` defaults to `8100/8101`.

For the current install, follow only:

- Quick Path step `1`
- Quick Path step `2`
- Quick Path step `3`
- Quick Path step `4`
- Quick Path step `5` only if HA is not ready yet
- Quick Path step `6` only later if failover is needed

Everything below `## 0. Confirmed Katilim Nexus Behavior` is reference and
troubleshooting material. It is not a second install flow.

Assumed values:

- `VM1=10.210.22.88`
- `VM2=10.210.22.89`
- `DEV_LB_IP=10.210.22.164`
- `POSTGRES_REPLICATION_NETWORK=10.210.22.0/24`
- delivery method: `Method D`

If Nexus requires login, run `docker login zknexus.ziraatkatilim.local:8181`
after Docker is configured on each VM. If it does not, skip that command.

Before step `1`, set the config bundle passphrase once on each VM shell:

```bash
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
```

If the VM layout has a small `/var` filesystem and Docker pulls fail with
`no space left on device`, move Docker storage to the root filesystem first.
Use this once per VM before Docker pulls or bootstrap:

```bash
sudo systemctl stop docker
```

```bash
sudo mkdir -p /docker-data
```

```bash
sudo rsync -aHAXx /var/lib/docker/ /docker-data/
```

```bash
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d_%H%M%S)
```

```bash
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "data-root": "/docker-data",
  "insecure-registries": ["zknexus.ziraatkatilim.local:8181"],
  "registry-mirrors": ["http://zknexus.ziraatkatilim.local:8181"]
}
EOF
```

```bash
sudo systemctl daemon-reload
```

```bash
sudo systemctl start docker
```

```bash
sudo systemctl status docker --no-pager -l
```

```bash
docker info | grep 'Docker Root Dir'
```

```bash
docker ps -a
```

```bash
docker volume ls
```

Do not delete `/var/lib/docker` until the VM is fully validated on the new
Docker root.

Keep that shell open until the bundle extraction is complete, then unset it:

```bash
unset CONFIG_BUNDLE_PASSPHRASE
```

If this VM already had a previous partial install attempt and you want to start
the runbook again from the pull/extract stage, that is supported.

Re-running the pull/extract steps overwrites:

- `/opt/orbina/internal_services`
- `/opt/orbina/incoming/ha.vm1.env`
- `/opt/orbina/incoming/ha.vm2.env`
- the managed service `.env` files restored by the encrypted config image

It does not automatically wipe:

- Docker named volumes
- already-created containers
- `/etc/internal-services/ha.env`
- `/etc/pki/tls/certs/cert.pem`
- `/etc/pki/tls/private/private.key`

Safe restart path on a VM that only reached extraction or early installer
failure:

```bash
cd /opt/orbina/internal_services && sudo ops/ha/stop-active.sh || true
cd /opt/orbina/internal_services && sudo ops/ha/stop-passive.sh || true
docker ps -a
```

If the output only shows stopped or partially created containers from the same
internal-services attempt, you can start the runbook again from step `1` or
step `3` on that VM with the `r17` install tag and the current config tag.

Do not delete Docker volumes unless you explicitly want to discard old state.

If you already have a LiteLLM image tar and want to use it instead of pulling
LiteLLM through Nexus, place it here before running `install-node.sh`:

- `/opt/orbina/incoming/litellm-image.tar`

The installer checks that path automatically and loads the tar before the image
pull step.

Optional manual pre-check on the VM:

```bash
ls -lh /opt/orbina/incoming/litellm-image.tar
```

Optional manual preload on the VM if you want to inspect it first:

```bash
docker load -i /opt/orbina/incoming/litellm-image.tar
```

If you want to pull LiteLLM manually from Nexus instead of using a tar, use:

```bash
docker pull zknexus.ziraatkatilim.local:8181/berriai/litellm:main-latest
```

If the loaded image name is not already the compose-expected tag, retag it to:

```bash
docker tag <LOADED_IMAGE_REF> harbor.tool.zb/devops-images/berriai/litellm-database:main-latest-10-02-2026-certs
```

If you pulled from Nexus directly, the exact retag command is:

```bash
docker tag zknexus.ziraatkatilim.local:8181/berriai/litellm:main-latest harbor.tool.zb/devops-images/berriai/litellm-database:main-latest-10-02-2026-certs
```

Then continue with the normal `install-node.sh` command. The installer will see
the target image already present and skip pulling LiteLLM from Nexus.

If Ragflow MinIO still pulls as `arm64` on a VM even after the mirror tag was
fixed, the most likely cause is a stale Nexus cache for the old tag manifest.
In that case, force the corrected amd64 image by digest before bootstrap:

```bash
docker image rm -f aliennor/ragflow-minio:RELEASE.2025-06-13T11-33-47Z 2>/dev/null || true
docker pull --platform linux/amd64 aliennor/ragflow-minio@sha256:acf456514a4a67dc3b4bc1e0dd522d52b7b7afcc3614dba12b324c17759c38db
docker tag aliennor/ragflow-minio@sha256:acf456514a4a67dc3b4bc1e0dd522d52b7b7afcc3614dba12b324c17759c38db aliennor/ragflow-minio:RELEASE.2025-06-13T11-33-47Z
docker image inspect aliennor/ragflow-minio:RELEASE.2025-06-13T11-33-47Z --format '{{.Architecture}} {{.Os}}'
```

Expected result:

- `amd64 linux`

After that, rerun `bootstrap-vm1-active.sh`.

### 1. On `VM1`

```bash
sudo mkdir -p /etc/docker
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
sudo sh -c 'printf "%s\n" "{\"insecure-registries\":[\"zknexus.ziraatkatilim.local:8181\"],\"registry-mirrors\":[\"http://zknexus.ziraatkatilim.local:8181\"]}" > /etc/docker/daemon.json'
sudo systemctl restart docker

curl -vk http://zknexus.ziraatkatilim.local:8181/v2/

# Optional only if Nexus pull requires auth
docker login zknexus.ziraatkatilim.local:8181

docker pull aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r19
docker pull aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9

docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r19 /output
docker run --rm -e CONFIG_BUNDLE_MODE=force -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" -v /opt/orbina:/output aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9 /output

cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh --role active
sudo ops/install/katilim/bootstrap-vm1-active.sh

curl -fsS http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status
sudo ops/install/katilim/smoke-test-active.sh
docker ps
unset CONFIG_BUNDLE_PASSPHRASE
```

`bootstrap-vm1-active.sh` now waits for the local HA readiness endpoint to
turn healthy before it runs the final smoke test.

At this point `VM1` should be the working server.

### 2. Browser Test Through HTTP During Installation

This snapshot is preconfigured for first-install HTTP access:

- nginx already accepts the Katilim dev hostnames on port `80`
- the old `.zb` names are still accepted for compatibility
- `install-node.sh` generates a temporary self-signed TLS certificate if no
  final certificate is present yet
- final DNS and real TLS can be switched in later without changing the app
  routing again

Map these hosts temporarily to `10.210.22.164`:

- `zfgasistan.yzyonetim-dev.ziraatkatilim.local`
- `manavgat.yzyonetim-dev.ziraatkatilim.local`
- `aykal.yzyonetim-dev.ziraatkatilim.local`
- `mercek.yzyonetim-dev.ziraatkatilim.local`

If the dev LB is not routing yet, temporarily map them to `10.210.22.88`
instead.

Then test:

- `http://zfgasistan.yzyonetim-dev.ziraatkatilim.local`
- `http://manavgat.yzyonetim-dev.ziraatkatilim.local`
- `http://aykal.yzyonetim-dev.ziraatkatilim.local`
- `http://mercek.yzyonetim-dev.ziraatkatilim.local`

### 3. On `VM2`

```bash
sudo mkdir -p /etc/docker
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
sudo sh -c 'printf "%s\n" "{\"insecure-registries\":[\"zknexus.ziraatkatilim.local:8181\"],\"registry-mirrors\":[\"http://zknexus.ziraatkatilim.local:8181\"]}" > /etc/docker/daemon.json'
sudo systemctl restart docker

curl -vk http://zknexus.ziraatkatilim.local:8181/v2/

# Optional only if Nexus pull requires auth
docker login zknexus.ziraatkatilim.local:8181

docker pull aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17
docker pull aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9

docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17 /output
docker run --rm -e CONFIG_BUNDLE_MODE=force -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" -v /opt/orbina:/output aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9 /output

cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh --role passive
sudo ops/install/katilim/bootstrap-vm2-passive.sh

curl -i http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status
docker ps
unset CONFIG_BUNDLE_PASSPHRASE
```

Expected on `VM2`:

- `/ready` returns `503`
- `/status` shows passive role

### 4. Back On `VM1`, Enable Sync

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/enable-vm1-passive-sync.sh

systemctl status internal-services-ha-sync-light.timer --no-pager
systemctl status internal-services-ha-sync-heavy.timer --no-pager
```

### 5. If The 2-VM Flow Is Not Ready

Keep `VM1` serving by itself:

```bash
cd /opt/orbina/internal_services
sudo ops/ha/start-single-node-fallback.sh
curl -fsS http://127.0.0.1:18081/ready
```

### 6. Promotion Later If Needed

On `VM2`:

```bash
cd /opt/orbina/internal_services
sudo ops/ha/promote-passive.sh
```

## 0. Confirmed Katilim Nexus Behavior

These results are already confirmed from a Katilim VM:

```bash
curl -vk http://zknexus.ziraatkatilim.local:8181/v2/
```

Expected result:

- HTTP `401 Unauthorized`
- `Docker-Distribution-Api-Version: registry/2.0`

This means:

- `zknexus.ziraatkatilim.local:8181` is a valid Docker registry connector
- it is plain HTTP, not HTTPS
- Docker must treat it as an insecure registry

These are not valid tests for Docker registry health:

- `curl http://zknexus.ziraatkatilim.local:8181/`
- `curl https://zknexus.ziraatkatilim.local:8181/v2/`

The first returns `400 Not a Docker request` and the second fails because that
connector does not speak HTTPS.

## 1. Pick The Delivery Method

Choose one of these:

- `Method A` recommended for first install: copy the prepared tree directly with `push-to-vms.sh`
- `Method B`: deliver the prepared tree as the install bundle image or install bundle tar
- `Method C` recommended when you cannot copy files and do not want manual config creation:
  pull the install bundle plus a separate private secure-config image
- `Method D` recommended when you need public pull-only delivery:
  pull the install bundle plus a public encrypted config image

Use `Method A` first if you want the least dependency on registry behavior.

Important meaning of `Method B`:

- it only changes how the prepared `internal_services` tree reaches the VM
- it does not magically include live `.env` files or TLS material
- the pullable install bundle is intentionally sanitized

So if you cannot copy files to the server at all, `Method B` solves:

- installer scripts
- compose files
- HA scripts
- runbooks

but it does not solve:

- service `.env` files
- `/etc/internal-services/ha.env`
- optional TLS keypair
- optional packaged Ragflow volume export

For a true no-copy installation you must do one of these:

1. create those files manually on the VM
2. have someone place the secure config bundle on the VM
3. later build a private config artifact for Nexus instead of public Hub

`Method C` is that private config artifact path.

`Method D` is the public-safe version of that idea: the config artifact is
encrypted before image build and unlocked on the VM with a passphrase.

## 2. On The Workstation: Prepare Inventory

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
cp ops/install/katilim/inventory.env.example ops/install/katilim/inventory.env
```

Edit:

- `ops/install/katilim/inventory.env`

Minimum fields:

- `VM1_HOST`
- `VM2_HOST`
- `POSTGRES_REPLICATION_PASSWORD`
- `POSTGRES_REPLICATION_NETWORK`

Set Nexus values exactly like this unless the Katilim environment changes:

```dotenv
NEXUS_DOCKER_REGISTRY=zknexus.ziraatkatilim.local:8181
NEXUS_DOCKER_SCHEME=http
NEXUS_REGISTRY_MIRROR_URL=http://zknexus.ziraatkatilim.local:8181
NEXUS_INSECURE_REGISTRY=true
AUTO_CONFIGURE_DOCKER_NEXUS=true
```

If Nexus requires auth, also set:

- `NEXUS_USERNAME`
- `NEXUS_PASSWORD`

Recommended first-test values:

```dotenv
ENABLE_QDRANT=true
ENABLE_RAGFLOW_STACK=true
ENABLE_OBSERVABILITY=true
COPY_TLS=false
GENERATE_SELF_SIGNED_TLS=true
```

If you already have the packaged Ragflow export from the older offline deploy
flow, set:

```dotenv
LOCAL_RAGFLOW_VOLUME_EXPORT_DIR=/path/to/ragflow_volumes_export
```

If you later want to carry the exact current LiteLLM image from an existing
company server, set:

```dotenv
LOCAL_LITELLM_IMAGE_TAR=/path/to/litellm-image.tar
```

## 3. Optional: Export LiteLLM Image On The Workstation

Use this only if you want to preload the exact current LiteLLM image instead of
the temporary fallback source.

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
bash ops/install/katilim/export-litellm-image.sh /tmp/litellm-image.tar
```

Then set:

```dotenv
LOCAL_LITELLM_IMAGE_TAR=/tmp/litellm-image.tar
```

in `ops/install/katilim/inventory.env`.

If you already have the tar on the VM and are following the public pull-only
path, you do not need this workstation step. Just place the tar at:

- `/opt/orbina/incoming/litellm-image.tar`

before running `install-node.sh` on that VM.

## 4. Deliver The Install Tree To Both VMs

### Method A: Direct Transfer With `push-to-vms.sh`

Recommended first install path:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
bash ops/install/katilim/push-to-vms.sh ops/install/katilim/inventory.env
```

This does all of the following:

- renders `ha.vm1.env` and `ha.vm2.env`
- copies the clean `internal_services` tree to both VMs
- copies the HA env files into `/opt/orbina/incoming`
- copies TLS files if configured
- copies the local LiteLLM image tar if configured
- copies the packaged Ragflow export to `VM1` if configured

### Method B: Install Bundle Image Or Tar

Build or reuse the already prepared bundle image:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09
bash katilim_install_bundle_2026_03_10/build-bundle-image.sh aliennor katilim-2vm-2026-03-10-r17 load
```

Optional push path:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09
bash katilim_install_bundle_2026_03_10/build-bundle-image.sh aliennor katilim-2vm-2026-03-10-r17 push
```

If you want a tar fallback instead of pulling the bundle from a registry:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09
bash katilim_install_bundle_2026_03_10/export-bundle-image.sh aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17 /tmp/internal-services-katilim-install.tar.gz
```

Build the secure config bundle:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09/internal_services
bash ops/install/katilim/prepare-secure-config-bundle.sh ops/install/katilim/inventory.env /tmp/katilim-secure-config.tar.gz
```

Copy the secure config bundle to both VMs:

```bash
scp /tmp/katilim-secure-config.tar.gz root@${VM1_HOST}:/opt/orbina/incoming/
scp /tmp/katilim-secure-config.tar.gz root@${VM2_HOST}:/opt/orbina/incoming/
```

If using the bundle tar fallback, copy it too:

```bash
scp /tmp/internal-services-katilim-install.tar.gz root@${VM1_HOST}:/opt/orbina/incoming/
scp /tmp/internal-services-katilim-install.tar.gz root@${VM2_HOST}:/opt/orbina/incoming/
```

On each VM, either pull the install bundle image after Docker is configured or
load the tar:

```bash
docker load -i /opt/orbina/incoming/internal-services-katilim-install.tar.gz
docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17 /output
```

Then apply the secure config bundle:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/apply-secure-config-bundle.sh /opt/orbina/incoming/katilim-secure-config.tar.gz /opt/orbina
```

### Method B Without Any File Copy

If you cannot copy files to the server and still want a pull-first path:

1. pull or load the install bundle image on the VM
2. extract it into `/opt/orbina`
3. create the required `.env` files on the VM manually
4. create `/opt/orbina/incoming/ha.vm1.env` and `/opt/orbina/incoming/ha.vm2.env` manually
5. continue with `install-node.sh`

This is operationally possible, but it is more manual than using the secure
config bundle.

If you want the least manual path without copying files, the better long-term
approach is a private config artifact in Nexus, not public Docker Hub.

### Method C: Pull The Install Bundle And A Private Secure-Config Image

Use this if:

- you cannot `scp` files to the VM
- you do not want to create `.env` files manually
- you can pull from a private registry path reachable through Katilim Nexus

On the workstation, build the private secure-config image from the real envs:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09
bash katilim_secure_config_bundle_2026_03_10/build-secure-config-image.sh internal_services/ops/install/katilim/inventory.env aliennor/internal-services-katilim-config:katilim-2vm-2026-03-10-r9 load
```

Important:

- this image contains live `.env` files and HA env files
- do not publish it to a public Docker Hub repository
- use only a private Docker Hub repository or a private Nexus-hosted path

On the VM, after Docker is configured for Katilim Nexus:

```bash
docker pull aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17
docker pull aliennor/internal-services-katilim-config:katilim-2vm-2026-03-10-r9
```

Extract both:

```bash
docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17 /output
docker run --rm -e CONFIG_BUNDLE_MODE=force -v /opt/orbina:/output aliennor/internal-services-katilim-config:katilim-2vm-2026-03-10-r9 /output
```

After that, continue directly to `install-node.sh`.

### Method D: Pull The Install Bundle And A Public Encrypted Config Image

Use this if:

- you cannot copy files to the VM
- you do not want to create `.env` files manually
- you need the config artifact to be publishable publicly

On the workstation, build the encrypted config image from the real envs:

```bash
cd /Users/batur/Desktop/2025_2026_Stuff/arf_project/internal_services_image_2026_03_09
bash katilim_encrypted_config_bundle_2026_03_10/build-encrypted-config-image.sh internal_services/ops/install/katilim/inventory.env aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9 load
```

You will be prompted for a passphrase during build if
`CONFIG_BUNDLE_PASSPHRASE` is not already set.

This image can be published publicly because the config bundle inside it is
encrypted. Do not share the passphrase in the same place as the image.

On the VM, after Docker is configured for Katilim Nexus:

```bash
docker pull aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17
docker pull aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9
```

Extract the install tree:

```bash
docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17 /output
```

Then unlock and extract the encrypted config image:

```bash
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
docker run --rm -e CONFIG_BUNDLE_MODE=force -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" -v /opt/orbina:/output aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9 /output
unset CONFIG_BUNDLE_PASSPHRASE
```

After that, continue directly to `install-node.sh`.

## 5. Configure Docker For Katilim Nexus On Each VM

If you used `Method A`, `install-node.sh` can do this automatically from the
rendered HA env. The manual version is here for validation and emergency use.

On each VM:

```bash
sudo mkdir -p /etc/docker
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
sudo sh -c 'printf "%s\n" "{\"insecure-registries\":[\"zknexus.ziraatkatilim.local:8181\"],\"registry-mirrors\":[\"http://zknexus.ziraatkatilim.local:8181\"]}" > /etc/docker/daemon.json'
sudo systemctl restart docker
docker info | grep -A5 -E 'Insecure Registries|Registry Mirrors'
```

Validate the connector:

```bash
curl -vk http://zknexus.ziraatkatilim.local:8181/v2/
```

Optional direct pull checks:

```bash
docker pull zknexus.ziraatkatilim.local:8181/library/postgres:15
docker pull zknexus.ziraatkatilim.local:8181/aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17
```

If pull auth is required:

```bash
docker login zknexus.ziraatkatilim.local:8181
```

## 6. Bring Up `VM1` First

Before this step, make sure these files exist either from the secure config
bundle, from one of the config images, or from manual creation on the VM:

- `phoenix/.env`
- `phoenix-reporting/.env`
- `litellm/.env`
- `n8n/.env`
- `openweb-ui/.env`
- `observability/.env`
- `qdrant/.env`
- `/opt/orbina/incoming/ha.vm1.env`
- `/opt/orbina/incoming/ha.vm2.env`

If you use `Method C`, they are created by the private secure-config image.

If you use `Method D`, they are created by the encrypted config image.

On `VM1`:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh --role active
sudo ops/install/katilim/bootstrap-vm1-active.sh
```

If `/opt/orbina/incoming/litellm-image.tar` exists, `install-node.sh` loads it
first and uses that local LiteLLM image instead of pulling LiteLLM through
Nexus.

What this does:

- installs `/etc/internal-services/ha.env`
- configures Docker daemon settings for the Katilim Nexus connector
- validates the Nexus Docker endpoint
- pulls and retags application images
- restores `/opt/orbina/incoming/ragflow_volumes_export` automatically if present
- starts the active stack
- prepares PostgreSQL replication on the active node
- runs the active smoke test

At this point `VM1` should be a working server even if `VM2` is not ready yet.

## 7. Validate `VM1`

On `VM1`:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/smoke-test-active.sh
curl -fsS http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status
docker ps
```

Expected result:

- HA `/ready` returns `200`
- the main application containers are running
- `VM1` serves traffic by itself

Browser validation from your workstation:

Add temporary hosts entries pointing to `10.210.22.164`:

```text
10.210.22.164 zfgasistan.yzyonetim-dev.ziraatkatilim.local
10.210.22.164 manavgat.yzyonetim-dev.ziraatkatilim.local
10.210.22.164 aykal.yzyonetim-dev.ziraatkatilim.local
10.210.22.164 mercek.yzyonetim-dev.ziraatkatilim.local
```

If the load balancer is not routing to `VM1` yet, temporarily point those
names to `10.210.22.88` instead.

Then open:

- `http://zfgasistan.yzyonetim-dev.ziraatkatilim.local`
- `http://manavgat.yzyonetim-dev.ziraatkatilim.local`
- `http://aykal.yzyonetim-dev.ziraatkatilim.local`
- `http://mercek.yzyonetim-dev.ziraatkatilim.local`

HTTPS is still available later, but the initial installation path is now
intended to work over HTTP first.

## 8. Ragflow Restore And Enablement

If `LOCAL_RAGFLOW_VOLUME_EXPORT_DIR` was set earlier, the packaged Ragflow
export should already be on `VM1` at:

- `/opt/orbina/incoming/ragflow_volumes_export`

and `bootstrap-vm1-active.sh` restores it automatically.

If you are not copying the export folder and want the VM to pull it instead,
keep this in the inventory:

```dotenv
RAGFLOW_EXPORT_IMAGE=aliennor/redis-11.03-ragflow-volumes:latest
RAGFLOW_EXPORT_IMAGE_PATH=/etc/redis/ragflow_volumes_export
```

Then `bootstrap-vm1-active.sh` pulls that image, extracts the export into
`/opt/orbina/incoming/ragflow_volumes_export`, and restores it automatically.

If you need to rerun the restore manually:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/restore-ragflow-volumes.sh /opt/orbina/incoming/ragflow_volumes_export
```

Expected packaged contents:

- `volume-names.txt`
- `SHA256SUMS.txt`
- `esdata01*.tar.gz`
- `minio_data*.tar.gz`
- `mysql_data*.tar.gz`
- `redis_data*.tar.gz`
- `qdrant_data*.tar.gz`

Ragflow is now part of the default install path. If you intentionally kept an
older server on `ENABLE_RAGFLOW_STACK=false`, switch it on like this:

```bash
cd /opt/orbina/internal_services
sudo sed -i.bak 's/^ENABLE_RAGFLOW_STACK=.*/ENABLE_RAGFLOW_STACK=true/' /etc/internal-services/ha.env
sudo ops/ha/stop-active.sh || true
sudo ops/ha/start-single-node-fallback.sh
```

## 8A. Apply Ragflow To An Already-Installed Core-Only Server

Use this if the server was already installed earlier with `ENABLE_RAGFLOW_STACK=false`.

On `VM1`:

```bash
read -rsp 'Config bundle passphrase: ' CONFIG_BUNDLE_PASSPHRASE; echo
docker pull aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17
docker pull aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9
docker run --rm -e BUNDLE_MODE=force -v /opt/orbina:/output aliennor/internal-services-katilim-install:katilim-2vm-2026-03-10-r17 /output
docker run --rm -e CONFIG_BUNDLE_MODE=force -e CONFIG_BUNDLE_PASSPHRASE="$CONFIG_BUNDLE_PASSPHRASE" -v /opt/orbina:/output aliennor/internal-services-katilim-config-encrypted:katilim-2vm-2026-03-10-r9 /output
unset CONFIG_BUNDLE_PASSPHRASE
sudo sed -i.bak 's/^ENABLE_RAGFLOW_STACK=.*/ENABLE_RAGFLOW_STACK=true/' /etc/internal-services/ha.env
cd /opt/orbina/internal_services
sudo ops/install/katilim/pull-ragflow-volume-export-image.sh /opt/orbina/incoming/ragflow_volumes_export aliennor/redis-11.03-ragflow-volumes:latest /etc/redis/ragflow_volumes_export
sudo ops/install/katilim/restore-ragflow-volumes.sh /opt/orbina/incoming/ragflow_volumes_export
sudo ops/ha/stop-active.sh || true
sudo ops/ha/start-single-node-fallback.sh
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'ragflow|mcp|qdrant'
```

On `VM2`, prepare the same future promotion behavior:

```bash
sudo sed -i.bak 's/^ENABLE_RAGFLOW_STACK=.*/ENABLE_RAGFLOW_STACK=true/' /etc/internal-services/ha.env
```

## 9. Bring Up `VM2` As Passive

On `VM2`:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/install-node.sh --role passive
sudo ops/install/katilim/bootstrap-vm2-passive.sh
```

The same LiteLLM tar rule applies on `VM2` if you place the tar at
`/opt/orbina/incoming/litellm-image.tar` before the install step.

Validate on `VM2`:

```bash
curl -i http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status
docker ps
```

Expected result:

- `/ready` returns `503`
- `/status` shows passive role
- PostgreSQL is standby
- public application services stay stopped

## 10. Enable Sync From `VM1` To `VM2`

Back on `VM1`:

```bash
cd /opt/orbina/internal_services
sudo ops/install/katilim/enable-vm1-passive-sync.sh
```

This performs the initial sync and enables the periodic sync timers.

Useful checks:

```bash
systemctl status internal-services-ha-sync-light.timer
systemctl status internal-services-ha-sync-heavy.timer
ls -l /var/lib/internal-services-ha
```

## 11. Load Balancer Health Check

The external LB should use only:

- `http://VM1:18081/ready`
- `http://VM2:18081/ready`

Expected behavior:

- active healthy node returns `200`
- passive healthy standby returns `503`
- unhealthy active node returns `503`

Do not use the public application URLs for failover control.

## 12. Promotion Later If `VM1` Fails

If `VM1` fails and `VM2` must become active:

On `VM2`:

```bash
cd /opt/orbina/internal_services
sudo ops/ha/promote-passive.sh
```

After promotion:

- move LB traffic to `VM2`
- verify:

```bash
curl -fsS http://127.0.0.1:18081/ready
curl -sS http://127.0.0.1:18081/status
```

## 13. Failback Preparation

After `VM2` is the confirmed primary and `VM1` is repaired:

On `VM1`:

```bash
cd /opt/orbina/internal_services
sudo ops/ha/prepare-failback.sh <VM2-IP>
```

This rebuilds `VM1` as the passive standby.

## 14. Single-VM Safe Fallback

If the 2-VM flow fails at any point and you need one working VM immediately,
keep traffic on `VM1` and run:

```bash
cd /opt/orbina/internal_services
sudo ops/ha/start-single-node-fallback.sh
curl -fsS http://127.0.0.1:18081/ready
```

This is the safe first-install fallback.

## 15. Which Files Matter Most

Main installer scripts:

- `ops/install/katilim/install-node.sh`
- `ops/install/katilim/bootstrap-vm1-active.sh`
- `ops/install/katilim/bootstrap-vm2-passive.sh`
- `ops/install/katilim/enable-vm1-passive-sync.sh`
- `ops/install/katilim/restore-ragflow-volumes.sh`
- `ops/install/katilim/configure-docker-daemon.sh`
- `ops/install/katilim/check-docker-registry-endpoint.sh`

Supporting HA scripts:

- `ops/ha/start-single-node-fallback.sh`
- `ops/ha/start-active.sh`
- `ops/ha/start-passive.sh`
- `ops/ha/promote-passive.sh`
- `ops/ha/prepare-failback.sh`

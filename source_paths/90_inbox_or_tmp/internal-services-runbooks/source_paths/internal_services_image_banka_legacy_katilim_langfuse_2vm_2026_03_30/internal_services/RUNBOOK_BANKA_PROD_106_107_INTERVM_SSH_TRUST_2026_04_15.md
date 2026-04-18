# Banka Prod 106/107 Inter-VM SSH Trust Runbook

Date: 2026-04-15

Use this for banka production only.

Targets:

- VM1 active: `10.11.115.106`
- VM2 passive: `10.11.115.107`
- SSH user: `root`

This prepares passwordless SSH both ways. The critical direction for HA sync is `106 -> 107`; the reverse `107 -> 106` is included because passive and failback operations are easier when both sides trust each other.

There are two ways to install the keys:

- Fast path: use `ssh-copy-id`. This asks once for the remote `root` password, then future SSH commands should not ask again.
- No remote password path: copy the public key text from one server and paste it into `/root/.ssh/authorized_keys` on the other server. Use this if you do not want to type the remote SSH password or do not have it, but you do have root console/sudo access on both VMs.

Run these commands from a root login shell on each machine:

```bash
sudo su -
```

## 1) On 106, Allow 106 To SSH Into 107

Run on `10.11.115.106`:

```bash
set -euo pipefail

systemctl enable --now sshd

mkdir -p /root/.ssh
chmod 700 /root/.ssh

if [ ! -f /root/.ssh/id_ed25519 ]; then
  ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ''
fi

touch /root/.ssh/known_hosts
chmod 600 /root/.ssh/known_hosts
ssh-keygen -R 10.11.115.107 >/dev/null 2>&1 || true
ssh-keyscan -H 10.11.115.107 >> /root/.ssh/known_hosts

ssh-copy-id -i /root/.ssh/id_ed25519.pub root@10.11.115.107

ssh -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.107 'hostname; whoami; echo 106_to_107_ok'
```

`ssh-copy-id` will ask for the `root@10.11.115.107` password once. If you cannot or do not want to enter that password, skip `ssh-copy-id` and use section 6 instead.

Expected final output includes:

```text
root
106_to_107_ok
```

## 2) On 107, Allow 107 To SSH Into 106

Run on `10.11.115.107`:

```bash
set -euo pipefail

systemctl enable --now sshd

mkdir -p /root/.ssh
chmod 700 /root/.ssh

if [ ! -f /root/.ssh/id_ed25519 ]; then
  ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ''
fi

touch /root/.ssh/known_hosts
chmod 600 /root/.ssh/known_hosts
ssh-keygen -R 10.11.115.106 >/dev/null 2>&1 || true
ssh-keyscan -H 10.11.115.106 >> /root/.ssh/known_hosts

ssh-copy-id -i /root/.ssh/id_ed25519.pub root@10.11.115.106

ssh -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.106 'hostname; whoami; echo 107_to_106_ok'
```

`ssh-copy-id` will ask for the `root@10.11.115.106` password once. If you cannot or do not want to enter that password, skip `ssh-copy-id` and use section 6 instead.

Expected final output includes:

```text
root
107_to_106_ok
```

## 3) Final Validation From 106

Run on `10.11.115.106`:

```bash
set -euo pipefail

ssh -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.107 'echo ssh_106_to_107_ok'

if [ -f /etc/internal-services/ha.env ]; then
  grep -E '^(NODE_ROLE|PRIMARY_HOST|PEER_HOST|PASSIVE_SSH_HOST|PASSIVE_SSH_USER)=' /etc/internal-services/ha.env
else
  echo "/etc/internal-services/ha.env not present yet. This is OK before install-node."
fi
```

Expected SSH output:

```text
ssh_106_to_107_ok
```

If `/etc/internal-services/ha.env` exists on `106`, expected values are:

```text
NODE_ROLE=active
PRIMARY_HOST=10.11.115.106
PEER_HOST=10.11.115.107
PASSIVE_SSH_HOST=10.11.115.107
PASSIVE_SSH_USER=root
```

## 4) Final Validation From 107

Run on `10.11.115.107`:

```bash
set -euo pipefail

ssh -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.106 'echo ssh_107_to_106_ok'

if [ -f /etc/internal-services/ha.env ]; then
  grep -E '^(NODE_ROLE|PRIMARY_HOST|PEER_HOST|PASSIVE_SSH_HOST|PASSIVE_SSH_USER)=' /etc/internal-services/ha.env
else
  echo "/etc/internal-services/ha.env not present yet. This is OK before install-node."
fi
```

Expected SSH output:

```text
ssh_107_to_106_ok
```

If `/etc/internal-services/ha.env` exists on `107`, expected values are:

```text
NODE_ROLE=passive
PRIMARY_HOST=10.11.115.106
PEER_HOST=10.11.115.106
PASSIVE_SSH_HOST=10.11.115.106
PASSIVE_SSH_USER=root
```

## 5) Port Checks

Run on `10.11.115.106`:

```bash
set -euo pipefail

if command -v nc >/dev/null 2>&1; then
  nc -vz 10.11.115.107 22
else
  timeout 5 bash -lc '</dev/tcp/10.11.115.107/22' && echo '107 ssh port reachable'
fi
```

Run on `10.11.115.107` after VM1 PostgreSQL is running:

```bash
set -euo pipefail

if command -v nc >/dev/null 2>&1; then
  nc -vz 10.11.115.106 5432
else
  timeout 5 bash -lc '</dev/tcp/10.11.115.106/5432' && echo '106 postgres port reachable'
fi
```

## 6) No Remote Password / Manual Public Key Paste Method

Use this section if `ssh-copy-id` is not installed, or if you do not want to enter the remote SSH password.

### 6.1) Allow 106 To SSH Into 107 Without Typing 107 Password

Run on `10.11.115.106`:

```bash
sudo su -

mkdir -p /root/.ssh
chmod 700 /root/.ssh

if [ ! -f /root/.ssh/id_ed25519 ]; then
  ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ''
fi

cat /root/.ssh/id_ed25519.pub
```

Copy the full single-line public key output.

Run on `10.11.115.107`:

```bash
sudo su -

mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
vi /root/.ssh/authorized_keys
```

Paste the public key line from `106` into `/root/.ssh/authorized_keys`, save, then validate from `106`:

```bash
sudo su -

ssh-keygen -R 10.11.115.107 >/dev/null 2>&1 || true
ssh-keyscan -H 10.11.115.107 >> /root/.ssh/known_hosts
ssh -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.107 'hostname; whoami; echo 106_to_107_ok'
```

### 6.2) Allow 107 To SSH Into 106 Without Typing 106 Password

Run on `10.11.115.107`:

```bash
sudo su -

mkdir -p /root/.ssh
chmod 700 /root/.ssh

if [ ! -f /root/.ssh/id_ed25519 ]; then
  ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ''
fi

cat /root/.ssh/id_ed25519.pub
```

Copy the full single-line public key output.

Run on `10.11.115.106`:

```bash
sudo su -

mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
vi /root/.ssh/authorized_keys
```

Paste the public key line from `107` into `/root/.ssh/authorized_keys`, save, then validate from `107`:

```bash
sudo su -

ssh-keygen -R 10.11.115.106 >/dev/null 2>&1 || true
ssh-keyscan -H 10.11.115.106 >> /root/.ssh/known_hosts
ssh -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.106 'hostname; whoami; echo 107_to_106_ok'
```

Then rerun sections 3 and 4.

## 7) If ssh-copy-id Is Missing But Password Login Is Allowed

Use this fallback from `106`:

```bash
cat /root/.ssh/id_ed25519.pub | ssh root@10.11.115.107 \
  'mkdir -p /root/.ssh && chmod 700 /root/.ssh && cat >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys'
```

Use this fallback from `107`:

```bash
cat /root/.ssh/id_ed25519.pub | ssh root@10.11.115.106 \
  'mkdir -p /root/.ssh && chmod 700 /root/.ssh && cat >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys'
```

Then rerun sections 3 and 4.

## 8) What This Enables

This SSH trust enables:

- active-to-passive volume sync
- passive bootstrap helper actions
- later failover and failback operations

This does not replace:

- `install-node.sh` on both VMs
- `bootstrap-vm1-active.sh` on `106`
- `bootstrap-vm2-passive.sh` on `107`
- PostgreSQL replication validation
- future load balancer cutover

# Banka Prod 106/107 Inter-VM SSH Trust Runbook

Date: 2026-04-18

Use this for banka production only.

Targets:

- VM1 active: `10.11.115.106`
- VM2 passive: `10.11.115.107`
- SSH user: `root`
- SSH port: `22`

This prepares passwordless SSH in both directions. The critical direction for HA sync is `106 -> 107`; the reverse `107 -> 106` is required for failback and passive-driven operations, so it is included as a first-class step, not as optional.

This runbook uses only the passwordless / no-remote-password path. You do NOT need the `root` password of either VM. You only need root console / sudo access on each VM. Keys are installed by copy-pasting the public key text between VMs. `ssh-copy-id` is not used.

Supersedes `RUNBOOK_BANKA_PROD_106_107_INTERVM_SSH_TRUST_2026_04_15.md`.

## Summary Of Steps

- Step 0: On BOTH VMs, make sure sshd allows root login by public key.
- Step 1: On 106, generate a key and print its public half.
- Step 2: On 107, paste 106's public key into `/root/.ssh/authorized_keys`.
- Step 3: On 106, validate 106 -> 107.
- Step 4: On 107, generate a key and print its public half.
- Step 5: On 106, paste 107's public key into `/root/.ssh/authorized_keys`.
- Step 6: On 107, validate 107 -> 106.
- Step 7: Port checks and wrap-up.

Open a root shell on each VM before starting:

```bash
sudo su -
```

## Step 0: On BOTH VMs, Allow Root Public Key Login

Known issue: on this `106/107` pair, `sshd` on `107` shipped with
`PermitRootLogin no`, which caused steps 2 and 3 to fail with
`Permission denied (publickey,...)` even though the `authorized_keys` line
was correct. `106` may have the same policy. This step fixes the policy on
each VM before any keys are touched.

Run on `10.11.115.106` AND on `10.11.115.107`:

```bash
set -euo pipefail

systemctl enable --now sshd

current=$(sshd -T 2>/dev/null | awk '/^permitrootlogin/ {print $2}')
echo "before: permitrootlogin=$current"

if [ "$current" != "yes" ] && [ "$current" != "prohibit-password" ]; then
  ts=$(date +%Y%m%d_%H%M%S)
  cp -a /etc/ssh/sshd_config "/etc/ssh/sshd_config.bak.$ts"

  mkdir -p /etc/ssh/sshd_config.d
  cat > /etc/ssh/sshd_config.d/50-banka-ha-root-pubkey.conf <<'EOF'
# Banka HA: allow root SSH login via public key only.
# Required for 106 <-> 107 passwordless trust used by HA sync and failback.
PermitRootLogin prohibit-password
EOF
  chmod 600 /etc/ssh/sshd_config.d/50-banka-ha-root-pubkey.conf

  sshd -t
  systemctl reload sshd

  after=$(sshd -T 2>/dev/null | awk '/^permitrootlogin/ {print $2}')
  echo "after drop-in: permitrootlogin=$after"

  if [ "$after" != "prohibit-password" ] && [ "$after" != "yes" ]; then
    sed -i.bak_banka 's/^PermitRootLogin no$/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
    sshd -t
    systemctl reload sshd
    after=$(sshd -T 2>/dev/null | awk '/^permitrootlogin/ {print $2}')
    echo "after sed: permitrootlogin=$after"
  fi
fi

sshd -T 2>/dev/null | grep -Ei '^(permitrootlogin|pubkeyauthentication|authorizedkeysfile)'
```

Expected final output on each VM:

```text
permitrootlogin prohibit-password
pubkeyauthentication yes
authorizedkeysfile .ssh/authorized_keys
```

Do not continue until both VMs show a `permitrootlogin` value of either
`prohibit-password` or `yes`. `prohibit-password` is preferred because it
still denies password-based root login.

## Step 1: On 106, Generate Key And Print Public Half

Run on `10.11.115.106`:

```bash
set -euo pipefail

mkdir -p /root/.ssh
chmod 700 /root/.ssh

if [ ! -f /root/.ssh/id_ed25519 ]; then
  ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ''
fi

touch /root/.ssh/known_hosts
chmod 600 /root/.ssh/known_hosts

cat /root/.ssh/id_ed25519.pub
```

Copy the entire single line starting with `ssh-ed25519 AAAA...` and ending
with the `root@...` comment. The pasted line must remain one line; do not
let your terminal wrap-copy split it.

## Step 2: On 107, Install 106's Public Key

Run on `10.11.115.107`:

```bash
set -euo pipefail

mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
chown -R root:root /root/.ssh
```

Append the public key from step 1 safely. Replace
`PASTE_THE_FULL_PUBKEY_LINE_FROM_106_HERE` with the one line you copied:

```bash
cat >> /root/.ssh/authorized_keys <<'EOF'
PASTE_THE_FULL_PUBKEY_LINE_FROM_106_HERE
EOF
```

Verify the installed line is intact:

```bash
awk '{print NR": fields="NF, "type="$1, "blob_head="substr($2,1,20)}' /root/.ssh/authorized_keys
```

Every line must report `fields=3` and a valid `type=` like `ssh-ed25519`. If
any line shows `fields=2` or a blank `type`, the paste got wrapped; delete
that line and redo this step.

If the host has SELinux enabled (`getenforce` is `Enforcing`), also run:

```bash
command -v restorecon >/dev/null && restorecon -R -v /root/.ssh || true
```

## Step 3: On 106, Validate 106 -> 107

Run on `10.11.115.106`:

```bash
set -euo pipefail

ssh-keygen -R 10.11.115.107 >/dev/null 2>&1 || true
ssh-keyscan -H 10.11.115.107 >> /root/.ssh/known_hosts

ssh -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.107 'hostname; whoami; echo 106_to_107_ok'
```

Expected output includes:

```text
root
106_to_107_ok
```

If this fails with `Permission denied (publickey,...)`, see the Troubleshooting section.

## Step 4: On 107, Generate Key And Print Public Half

Run on `10.11.115.107`:

```bash
set -euo pipefail

mkdir -p /root/.ssh
chmod 700 /root/.ssh

if [ ! -f /root/.ssh/id_ed25519 ]; then
  ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ''
fi

touch /root/.ssh/known_hosts
chmod 600 /root/.ssh/known_hosts

cat /root/.ssh/id_ed25519.pub
```

Copy the entire single line.

## Step 5: On 106, Install 107's Public Key

Run on `10.11.115.106`:

```bash
set -euo pipefail

mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
chown -R root:root /root/.ssh
```

Append the public key from step 4 safely. Replace
`PASTE_THE_FULL_PUBKEY_LINE_FROM_107_HERE` with the one line you copied:

```bash
cat >> /root/.ssh/authorized_keys <<'EOF'
PASTE_THE_FULL_PUBKEY_LINE_FROM_107_HERE
EOF
```

Verify intact lines:

```bash
awk '{print NR": fields="NF, "type="$1, "blob_head="substr($2,1,20)}' /root/.ssh/authorized_keys
```

If the host has SELinux enabled, also run:

```bash
command -v restorecon >/dev/null && restorecon -R -v /root/.ssh || true
```

## Step 6: On 107, Validate 107 -> 106

Run on `10.11.115.107`:

```bash
set -euo pipefail

ssh-keygen -R 10.11.115.106 >/dev/null 2>&1 || true
ssh-keyscan -H 10.11.115.106 >> /root/.ssh/known_hosts

ssh -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.106 'hostname; whoami; echo 107_to_106_ok'
```

Expected output includes:

```text
root
107_to_106_ok
```

## Step 7: Port Checks

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

## Troubleshooting: Permission Denied After Paste

If step 3 or step 6 fails with
`Permission denied (publickey,gssapi-keyex,gssapi-with-mic,password,keyboard-interactive)`
despite the public key clearly being in `authorized_keys` on the target VM,
walk through the published diagnostic checks on GitHub:

- Diagnostic: `https://github.com/Aliennor/internal-services-runbooks/blob/main/checks/CHECK_BANKA_PROD_106_107_SSH_TRUST_PERMISSION_DENIED_2026_04_18.md`
- Fix for `PermitRootLogin no` specifically: `https://github.com/Aliennor/internal-services-runbooks/blob/main/checks/CHECK_BANKA_PROD_107_ENABLE_ROOT_PUBKEY_LOGIN_2026_04_18.md`

The five causes these checks cover, in the order you should verify them:

1. sshd policy: `sshd -T` reports `permitrootlogin no`. Fix with Step 0 above.
2. Pasted key mangled: `authorized_keys` line has `fields != 3` or is wrapped.
3. Wrong permissions on `/root`, `/root/.ssh`, or `authorized_keys`.
4. Wrong SELinux context on `authorized_keys` on RHEL/Rocky.
5. Raw connectivity (firewall, sshd listening).

The fastest single command to classify which one you hit is, on the origin VM:

```bash
ssh -vvv -o BatchMode=yes -o ConnectTimeout=10 root@TARGET_IP true 2>&1 | tail -80
```

- `Server accepts key: ...` followed by `Authentications that can continue` and immediately on the target `ROOT LOGIN REFUSED FROM ...` in `journalctl -u sshd` → sshd policy (cause 1).
- Repeated `Offering public key: ...` without `Server accepts key` → key mismatch / mangled paste / wrong permissions / SELinux (causes 2-4).
- `kex_exchange_identification` or no banner → connectivity (cause 5).

## What This Enables

This SSH trust enables:

- Active-to-passive volume sync from `106` to `107`.
- Passive bootstrap helper actions from `107` touching `106`.
- Failover and failback operations in either direction.

This does not replace:

- `install-node.sh` on both VMs.
- `bootstrap-vm1-active.sh` on `106`.
- `bootstrap-vm2-passive.sh` on `107`.
- PostgreSQL replication validation.
- Future load balancer cutover.

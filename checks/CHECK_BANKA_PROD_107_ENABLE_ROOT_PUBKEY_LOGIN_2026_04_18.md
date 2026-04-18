# Banka Prod 107: Enable Root Pubkey Login (Root Cause Of 106 -> 107 SSH Denied)

## Root Cause (Confirmed)

From the prior diagnostic check, the evidence on `10.11.115.107` is:

- `sshd -T` reports: `permitrootlogin no`
- `/etc/ssh/sshd_config:40: PermitRootLogin no`
- `journalctl -u sshd` on `107` during a connect from `106` shows:
  `ROOT LOGIN REFUSED FROM 10.11.115.106`
- On `106`, `ssh -vvv` confirmed the key itself is accepted:
  `Server accepts key: /root/.ssh/id_ed25519 ED25519 SHA256:thsp...`

So the key exchange and the `authorized_keys` line are correct. The sshd on
`107` is explicitly refusing root logins regardless of key, and that is why
auth fails immediately after the key is accepted.

SELinux is `Disabled` on `107`, so SELinux is not a factor here. Permissions
and ownership are correct. The `restorecon` run was a no-op.

## Host Is FreeIPA-Enrolled

`107` has `/etc/ssh/sshd_config.d/04-ipa.conf` which sets:

```text
PubkeyAuthentication yes
```

This tells us FreeIPA / ipa-client-install manages sshd config on this host
via a drop-in. To avoid future IPA upgrades overwriting our change (or
conflicting with IPA policy), do the same: add our setting as a drop-in file
with a lower-priority prefix, not by editing `/etc/ssh/sshd_config` directly.

## Fix: Allow Root Login By Public Key Only (Safest)

`prohibit-password` is the safest setting for HA: root may log in with a
valid key but cannot log in with a password. This matches what the install
and HA runbooks expect for the active/passive pair.

Run on `10.11.115.107`:

```bash
set -euo pipefail

sudo su -

ts=$(date +%Y%m%d_%H%M%S)
cp -a /etc/ssh/sshd_config "/etc/ssh/sshd_config.bak.$ts"

mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/50-banka-ha-root-pubkey.conf <<'EOF'
# Banka HA: allow root SSH login via public key only.
# Added 2026-04-18 to fix 106 -> 107 passwordless SSH for HA sync.
PermitRootLogin prohibit-password
EOF
chmod 600 /etc/ssh/sshd_config.d/50-banka-ha-root-pubkey.conf

sshd -t
systemctl reload sshd

sshd -T 2>/dev/null | grep -Ei '^(permitrootlogin|pubkeyauthentication|passwordauthentication)'
```

Expected `sshd -T` output after reload:

```text
permitrootlogin prohibit-password
pubkeyauthentication yes
passwordauthentication yes
```

Note: `sshd_config.d/*.conf` is processed in lexical order, and for `Match`
blocks "first match wins", but for simple global keywords the FIRST
occurrence across the merged config wins. Red Hat ships
`/etc/ssh/sshd_config` with `PermitRootLogin no` on line 40 and includes
drop-ins BEFORE main config is processed in most recent builds, which is
why our drop-in `50-*` works. If after reload `sshd -T` still reports
`permitrootlogin no`, proceed to the override section below.

### If `sshd -T` Still Shows `permitrootlogin no` After Reload

This means `/etc/ssh/sshd_config` is being read before drop-ins on this
host. Fix by editing the main file directly:

```bash
sudo su -

sed -i.bak_banka 's/^PermitRootLogin no$/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
grep -nE '^PermitRootLogin' /etc/ssh/sshd_config

sshd -t
systemctl reload sshd

sshd -T 2>/dev/null | grep -Ei '^(permitrootlogin|pubkeyauthentication|passwordauthentication)'
```

## Validate From 106

Run on `10.11.115.106`:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.107 'hostname; whoami; echo 106_to_107_ok'
```

Expected output:

```text
zb1plorbiarfa02...
root
106_to_107_ok
```

Then repeat the mirror direction for HA symmetry. Run on `10.11.115.107`:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.106 'hostname; whoami; echo 107_to_106_ok'
```

Expected output:

```text
zb1plorbiarfa01...
root
107_to_106_ok
```

If the reverse direction also fails with "Permission denied", check that
`/etc/ssh/sshd_config` on `106` does not also have `PermitRootLogin no`.
If so, apply the same drop-in fix on `106`.

## Rollback

If this change must be reverted (for example because corporate hardening
policy forbids root SSH even by key):

```bash
sudo su -
rm -f /etc/ssh/sshd_config.d/50-banka-ha-root-pubkey.conf
# If the sed fallback was used, restore the backup too:
test -f /etc/ssh/sshd_config.bak_banka && \
  mv /etc/ssh/sshd_config.bak_banka /etc/ssh/sshd_config
sshd -t
systemctl reload sshd
sshd -T 2>/dev/null | grep -Ei '^permitrootlogin'
```

Be aware: reverting will break `106 -> 107` passwordless SSH and therefore
break HA active-to-passive volume sync and failover automation.

## Security Notes

- `prohibit-password` keeps password-based root login off while allowing
  key-based root login. This is the accepted compromise for this HA pair and
  matches the SSH trust runbook's premise.
- Do not set `PermitRootLogin yes` here. That would additionally allow
  password root login, which corporate policy typically forbids and which
  widens the attack surface.
- Keep `passwordauthentication yes` only if non-root users need password
  login. If this host is key-only for everyone, consider a follow-up check
  to harden `passwordauthentication no` for non-root accounts as well.

## Send Back

- `sshd -T | grep permitrootlogin` output after reload.
- The `ssh ... 106_to_107_ok` result.
- The `ssh ... 107_to_106_ok` result.

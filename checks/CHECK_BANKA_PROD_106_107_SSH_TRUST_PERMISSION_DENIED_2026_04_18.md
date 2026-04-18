# Banka Prod 106 → 107 SSH Trust: Permission Denied Diagnostics

Symptom observed on `10.11.115.106`:

```text
root@10.11.115.107: Permission denied (publickey,gssapi-keyex,gssapi-with-mic,password,keyboard-interactive).
```

The user reports they already pasted `106`'s public key into
`/root/.ssh/authorized_keys` on `107`, but SSH from `106` still fails.

This check identifies which of the common root causes is actually triggering:

1. Pasted public key was mangled (line-wrapped, extra chars, missing fields).
2. Wrong filesystem permissions on `/root`, `/root/.ssh`, or `authorized_keys`.
3. Wrong SELinux context on `/root/.ssh/authorized_keys` (common on RHEL/Rocky
   when the file was created manually instead of via `ssh-copy-id`).
4. `sshd` on `107` disallows `PermitRootLogin` or `PubkeyAuthentication`.
5. Connectivity issue unrelated to keys (port/host).

## 1) On 106 — verbose SSH debug

Run on `10.11.115.106`:

```bash
ssh -vvv -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.107 true 2>&1 | tail -80
```

Interpretation:

- `Offering public key: /root/.ssh/id_ed25519` then `Server accepts key` → key
  path works; any failure after this is sshd policy.
- `Offering public key: ...` then `Authentications that can continue:
  publickey,...` repeatedly → server rejected this key. Go to sections 3, 4, 5.
- `no matching host key type found` / `kex_exchange_identification` → not a
  key problem. Go to section 6.

## 2) On 106 — print the real public key and its shape

Run on `10.11.115.106`:

```bash
cat /root/.ssh/id_ed25519.pub
awk '{print "fields="NF, "length="length($0)}' /root/.ssh/id_ed25519.pub
```

Expected:

- Single line starting with `ssh-ed25519 AAAA...`.
- `fields=3` (type, base64 blob, comment).
- `length=` around 100 or more.

## 3) On 107 — confirm the pasted key is actually intact

Run on `10.11.115.107`:

```bash
ls -la /root /root/.ssh /root/.ssh/authorized_keys
awk '{print NR": fields="NF, "length="length($0), "type="$1, "blob_head="substr($2,1,20)}' /root/.ssh/authorized_keys
```

What to check:

- `/root` mode `drwx------` or `drwxr-xr-x`. If `drwxrwx...`, group/other write
  breaks key auth.
- `/root/.ssh` mode `drwx------` (700), owner `root root`.
- `/root/.ssh/authorized_keys` mode `-rw-------` (600), owner `root root`.
- Every line in `authorized_keys` must report `fields=3` and `type=ssh-ed25519`
  (or `ssh-rsa`, `ecdsa-sha2-nistp256`, etc). A line with `fields=2` or a line
  that does not start with a valid key type is a pasted/wrapped key.
- Compare `blob_head` of the target key line here with `blob_head` of the
  output of section 2. They must match exactly.

Fix if permissions are wrong:

```bash
chown -R root:root /root/.ssh
chmod 700 /root/.ssh
chmod 600 /root/.ssh/authorized_keys
```

Fix if the line is mangled: delete the bad line and re-paste as one single
line, or use section 7 of the SSH trust runbook to install via `ssh-copy-id`.

## 4) On 107 — SELinux context

Run on `10.11.115.107`:

```bash
getenforce
ls -laZ /root/.ssh /root/.ssh/authorized_keys 2>/dev/null
```

Expected: contexts like `system_u:object_r:ssh_home_t:s0` on both
`.ssh` and `authorized_keys`. If you see `admin_home_t`, `user_home_t`, or
`unlabeled_t` on `authorized_keys` while `getenforce` is `Enforcing`, SELinux
is blocking key auth.

Fix:

```bash
restorecon -R -v /root/.ssh
```

## 5) On 107 — sshd policy

Run on `10.11.115.107`:

```bash
sshd -T 2>/dev/null | grep -Ei '^(permitrootlogin|pubkeyauthentication|authorizedkeysfile|passwordauthentication|usedns)'
```

Required:

- `permitrootlogin yes` or `permitrootlogin prohibit-password`.
- `pubkeyauthentication yes`.
- `authorizedkeysfile` includes `.ssh/authorized_keys` (the default is fine).

Also check for drop-in overrides:

```bash
grep -RniE '^(permitrootlogin|pubkeyauthentication|authorizedkeysfile)' \
  /etc/ssh/sshd_config /etc/ssh/sshd_config.d/ 2>/dev/null
```

If changes are required, edit the file reported by the grep, then:

```bash
sshd -t && systemctl reload sshd
```

## 6) On 107 — live sshd log while 106 tries to connect

Terminal A on `10.11.115.107`:

```bash
journalctl -u sshd -f
```

Terminal B on `10.11.115.106`:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.107 true
```

Interpret the lines printed on `107` as `106` connects:

- `Authentication refused: bad ownership or modes for directory /root` or
  `... for file /root/.ssh/authorized_keys` → fix with section 3 chmod/chown.
- `Authentication refused: bad ownership or modes for file
  /root/.ssh/authorized_keys` → 600 and root-owned.
- `Failed publickey for root from 10.11.115.106 ...` with no "Authentication
  refused" line → the key is not matching (mangled paste or wrong key). Go back
  to sections 2 and 3.
- `User root from 10.11.115.106 not allowed because ...` → sshd policy, fix
  with section 5.
- No new line appears on `107` at all → connectivity problem, section 7.

## 7) Connectivity sanity

Run on `10.11.115.106`:

```bash
nc -vz 10.11.115.107 22 || timeout 5 bash -lc '</dev/tcp/10.11.115.107/22' && echo 'port 22 reachable'
ssh-keyscan -T 5 10.11.115.107 2>/dev/null | head -2
```

- If `nc`/`/dev/tcp` fails → network or firewall, not SSH keys.
- If `ssh-keyscan` returns no banner → sshd not listening or filtered.

## 8) Safe fallback: reinstall the key from 106

If you would rather avoid paste-corruption entirely, from `10.11.115.106` run
the password-based reinstall (you must know `root@107`'s password):

```bash
cat /root/.ssh/id_ed25519.pub | ssh root@10.11.115.107 \
  'mkdir -p /root/.ssh && chmod 700 /root/.ssh && \
   cat >> /root/.ssh/authorized_keys && \
   chmod 600 /root/.ssh/authorized_keys && \
   command -v restorecon >/dev/null && restorecon -R -v /root/.ssh || true'
```

Or, if `ssh-copy-id` is installed:

```bash
ssh-copy-id -i /root/.ssh/id_ed25519.pub root@10.11.115.107
```

Then retest:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@10.11.115.107 \
  'hostname; whoami; echo 106_to_107_ok'
```

## Send Back

When pasting results, include:

- The last ~80 lines of `ssh -vvv` output from section 1.
- The `ls -laZ` output from sections 3 and 4.
- The `sshd -T | grep ...` output from section 5.
- Any relevant `journalctl -u sshd` lines from section 6.

That is enough to pinpoint which of the five failure modes is active and give
you the one exact fix to apply.

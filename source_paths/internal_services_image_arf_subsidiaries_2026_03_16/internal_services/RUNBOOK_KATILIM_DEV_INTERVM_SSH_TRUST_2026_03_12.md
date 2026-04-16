# Katilim Dev Inter-VM SSH Trust Runbook

Use this to make the two dev VMs trust each other for passwordless SSH.

Current dev VM IPs:

- `VM1=10.210.22.88`
- `VM2=10.210.22.89`

Current intended SSH user:

- `root`

For the active/passive flow, the critical direction is:

- `VM1 -> VM2`

The reverse direction is optional but recommended:

- `VM2 -> VM1`

## 1. On `VM1`, Create The SSH Key

```bash
mkdir -p /root/.ssh
```

```bash
chmod 700 /root/.ssh
```

```bash
ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ''
```

```bash
cat /root/.ssh/id_ed25519.pub
```

Copy the full single-line output from the last command.

## 2. On `VM2`, Allow `VM1` To Log In

```bash
mkdir -p /root/.ssh
```

```bash
chmod 700 /root/.ssh
```

```bash
echo 'PASTE_VM1_PUBLIC_KEY_HERE' >> /root/.ssh/authorized_keys
```

```bash
chmod 600 /root/.ssh/authorized_keys
```

## 3. Back On `VM1`, Test Passwordless SSH To `VM2`

```bash
ssh root@10.210.22.89 'echo ok'
```

Expected result:

- prints `ok`
- does not ask for password

If it asks about host authenticity the first time, type:

```bash
yes
```

## 4. Optional: Make `VM2 -> VM1` Work Too

On `VM2`:

```bash
mkdir -p /root/.ssh
```

```bash
chmod 700 /root/.ssh
```

```bash
ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ''
```

```bash
cat /root/.ssh/id_ed25519.pub
```

Copy the full single-line output.

On `VM1`:

```bash
echo 'PASTE_VM2_PUBLIC_KEY_HERE' >> /root/.ssh/authorized_keys
```

```bash
chmod 600 /root/.ssh/authorized_keys
```

Back on `VM2`:

```bash
ssh root@10.210.22.88 'echo ok'
```

## 5. Quick Network Checks

From `VM1`:

```bash
nc -vz 10.210.22.89 22
```

From `VM2`:

```bash
nc -vz 10.210.22.88 5432
```

Expected result:

- port `22` reachable on `VM2`
- port `5432` reachable on `VM1`

## 6. What This Solves

This SSH trust is enough for:

- sync scripts
- passive bootstrap helpers
- remote SSH actions from active to passive

It is not enough by itself for the whole HA system. The rest still needs:

- PostgreSQL replication
- the passive bootstrap
- sync timers
- correct env files on both VMs

## 7. Reuse For Other VM Pairs

To reuse this for another pair later:

- replace `10.210.22.88` with the new active node IP
- replace `10.210.22.89` with the new passive node IP
- keep the same command order

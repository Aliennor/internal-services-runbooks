# Katilim Prod Windows LiteLLM Test Runbook

Use this from a Windows machine or Windows Terminal session to test reachability
and LiteLLM behavior on the Katilim prod setup.

Current prod targets:

- `VM1=10.210.28.26`
- `VM2=10.210.28.27`
- `PROD_LB_IP=10.210.18.101`

Prod public hostnames:

- `manavgat.yzyonetim.ziraatkatilim.local`
- `zfgasistan.yzyonetim.ziraatkatilim.local`
- `aykal.yzyonetim.ziraatkatilim.local`
- `mercek.yzyonetim.ziraatkatilim.local`

LiteLLM exposure in the current stack:

- direct host port: `4000`
- nginx/LB hostname path: `http://manavgat.yzyonetim.ziraatkatilim.local/`

Current useful LiteLLM model names in prod:

- `gpt-oss-20b`
- `bge-m3`
- `jina-embed-v4`
- `dots-ocr`
- `qwen3-guard-4b`
- `qwen3-vl`
- `qwen3-8b-vl`

You need a valid LiteLLM bearer key for API calls:

- usually `LITELLM_MASTER_KEY`
- get it from the prod LiteLLM `.env` on the active VM or from the approved
  prod secret source

## 1. If Prod DNS Is Not Ready Yet

Edit this file as Administrator:

```text
C:\Windows\System32\drivers\etc\hosts
```

Add these lines to test through the current active prod VM directly:

```text
10.210.28.26 manavgat.yzyonetim.ziraatkatilim.local
10.210.28.26 zfgasistan.yzyonetim.ziraatkatilim.local
10.210.28.26 aykal.yzyonetim.ziraatkatilim.local
10.210.28.26 mercek.yzyonetim.ziraatkatilim.local
```

If the LB is already routing correctly, you can map them to the LB instead:

```text
10.210.18.101 manavgat.yzyonetim.ziraatkatilim.local
10.210.18.101 zfgasistan.yzyonetim.ziraatkatilim.local
10.210.18.101 aykal.yzyonetim.ziraatkatilim.local
10.210.18.101 mercek.yzyonetim.ziraatkatilim.local
```

## 2. Set The LiteLLM Key In Windows

### CMD

```cmd
set LITELLM_KEY=PASTE_REAL_LITELLM_MASTER_KEY_HERE
```

### PowerShell

```powershell
$env:LITELLM_KEY='PASTE_REAL_LITELLM_MASTER_KEY_HERE'
```

## 3. Basic Reachability Checks

### CMD: direct port reachability to the active VM

```cmd
curl.exe -I --max-time 10 http://10.210.28.26:4000/
```

```cmd
curl.exe -I --max-time 10 http://10.210.18.101/
```

### PowerShell: port tests

```powershell
Test-NetConnection 10.210.28.26 -Port 4000
```

```powershell
Test-NetConnection 10.210.18.101 -Port 80
```

### Optional Telnet checks

If Telnet Client is enabled on Windows:

```cmd
telnet 10.210.28.26 4000
```

```cmd
telnet 10.210.18.101 80
```

Expected result:

- connect succeeds to `10.210.28.26:4000`
- connect succeeds to `10.210.18.101:80`

If `VM2` is still passive, raw LiteLLM on `VM2` should usually not be the
serving endpoint:

```powershell
Test-NetConnection 10.210.28.27 -Port 4000
```

## 4. Raw LiteLLM API Tests Against `VM1:4000`

### List models

#### CMD

```cmd
curl.exe -sS http://10.210.28.26:4000/v1/models -H "Authorization: Bearer %LITELLM_KEY%"
```

#### PowerShell

```powershell
curl.exe -sS http://10.210.28.26:4000/v1/models -H "Authorization: Bearer $env:LITELLM_KEY"
```

### Confirm prod models exist

#### CMD

```cmd
curl.exe -sS http://10.210.28.26:4000/v1/models -H "Authorization: Bearer %LITELLM_KEY%" | findstr /I "gpt-oss-20b bge-m3 jina-embed-v4 qwen3-guard-4b qwen3-vl"
```

#### PowerShell

```powershell
curl.exe -sS http://10.210.28.26:4000/v1/models -H "Authorization: Bearer $env:LITELLM_KEY" | Select-String "gpt-oss-20b|bge-m3|jina-embed-v4|qwen3-guard-4b|qwen3-vl"
```

### Health-style HTTP check

```cmd
curl.exe -i http://10.210.28.26:4000/v1/models -H "Authorization: Bearer %LITELLM_KEY%"
```

Expected result:

- `HTTP/1.1 200`

## 5. Model Invocation Tests Against `VM1:4000`

### Chat completion test: `gpt-oss-20b`

#### CMD

```cmd
curl.exe -sS http://10.210.28.26:4000/v1/chat/completions -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"gpt-oss-20b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: prod-ok\"}],\"max_tokens\":16}"
```

#### PowerShell

```powershell
curl.exe -sS http://10.210.28.26:4000/v1/chat/completions -H "Authorization: Bearer $env:LITELLM_KEY" -H "Content-Type: application/json" -d "{\"model\":\"gpt-oss-20b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: prod-ok\"}],\"max_tokens\":16}"
```

Expected result:

- JSON response with a completion choice
- content close to `prod-ok`

### Embedding test: `bge-m3`

#### CMD

```cmd
curl.exe -sS http://10.210.28.26:4000/v1/embeddings -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"bge-m3\",\"input\":\"Ziraat Katilim production embedding test\"}"
```

#### PowerShell

```powershell
curl.exe -sS http://10.210.28.26:4000/v1/embeddings -H "Authorization: Bearer $env:LITELLM_KEY" -H "Content-Type: application/json" -d "{\"model\":\"bge-m3\",\"input\":\"Ziraat Katilim production embedding test\"}"
```

Expected result:

- JSON response with `data`
- at least one embedding vector

### Alternate embedding test: `jina-embed-v4`

```cmd
curl.exe -sS http://10.210.28.26:4000/v1/embeddings -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"jina-embed-v4\",\"input\":\"Jina embedding production test\"}"
```

### Guard model test: `qwen3-guard-4b`

```cmd
curl.exe -sS http://10.210.28.26:4000/v1/chat/completions -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"qwen3-guard-4b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: guard-ok\"}],\"max_tokens\":16}"
```

### Vision-family model basic text-only probe: `qwen3-vl`

```cmd
curl.exe -sS http://10.210.28.26:4000/v1/chat/completions -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"qwen3-vl\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: vl-ok\"}],\"max_tokens\":16}"
```

### OCR-family model basic probe: `dots-ocr`

```cmd
curl.exe -sS http://10.210.28.26:4000/v1/chat/completions -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"dots-ocr\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: ocr-ok\"}],\"max_tokens\":16}"
```

## 6. Test Through The Final Hostname Path

In this setup, nginx proxies the LiteLLM hostname route. The current LiteLLM
public hostname is:

- `manavgat.yzyonetim.ziraatkatilim.local`

### Direct browser/API style test

```cmd
curl.exe -sS http://manavgat.yzyonetim.ziraatkatilim.local/v1/models -H "Authorization: Bearer %LITELLM_KEY%"
```

### Chat completion through the final hostname

```cmd
curl.exe -sS http://manavgat.yzyonetim.ziraatkatilim.local/v1/chat/completions -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"gpt-oss-20b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: host-ok\"}],\"max_tokens\":16}"
```

## 7. Test Through LB IP Without DNS

If you do not want to edit the Windows hosts file yet, send the correct Host
header to the LB IP directly:

```cmd
curl.exe -sS http://10.210.18.101/v1/models -H "Host: manavgat.yzyonetim.ziraatkatilim.local" -H "Authorization: Bearer %LITELLM_KEY%"
```

```cmd
curl.exe -sS http://10.210.18.101/v1/chat/completions -H "Host: manavgat.yzyonetim.ziraatkatilim.local" -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"gpt-oss-20b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: lb-ok\"}],\"max_tokens\":16}"
```

## 8. Optional Verbose Troubleshooting Calls

### CMD verbose models call

```cmd
curl.exe -v http://10.210.28.26:4000/v1/models -H "Authorization: Bearer %LITELLM_KEY%"
```

### CMD verbose hostname call

```cmd
curl.exe -v http://manavgat.yzyonetim.ziraatkatilim.local/v1/models -H "Authorization: Bearer %LITELLM_KEY%"
```

### PowerShell full response capture

```powershell
$r = Invoke-WebRequest -Uri "http://10.210.28.26:4000/v1/models" -Headers @{ Authorization = "Bearer $env:LITELLM_KEY" }
$r.StatusCode
$r.Content
```

## 9. What Success Looks Like

Direct VM test success means:

- `10.210.28.26:4000` is reachable
- LiteLLM is listening
- your bearer key is accepted
- LiteLLM can list configured models
- at least one generation call and one embedding call succeed

Hostname/LB test success means:

- DNS or host-header routing is correct
- nginx/LB reaches the active VM
- the final production URL path is working, not just the raw container port

## 10. What Failure Means

- `Could not connect` or port failure:
  - network/firewall/LB/listener issue
- `401` or `403`:
  - wrong LiteLLM key
- `404` on `/v1/...` through hostname:
  - wrong hostname mapping or wrong reverse-proxy route
- model call fails but `/v1/models` works:
  - LiteLLM is up, but upstream gateway/model access is failing
- raw `VM1:4000` works but hostname/LB fails:
  - nginx/LB/DNS path issue

## 11. Minimal Fast Test Set

If you only want the shortest useful test set, run these:

```cmd
set LITELLM_KEY=PASTE_REAL_LITELLM_MASTER_KEY_HERE
```

```cmd
curl.exe -sS http://10.210.28.26:4000/v1/models -H "Authorization: Bearer %LITELLM_KEY%"
```

```cmd
curl.exe -sS http://10.210.28.26:4000/v1/chat/completions -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"gpt-oss-20b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: ok\"}],\"max_tokens\":16}"
```

```cmd
curl.exe -sS http://10.210.28.26:4000/v1/embeddings -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"bge-m3\",\"input\":\"test\"}"
```

```cmd
curl.exe -sS http://10.210.18.101/v1/models -H "Host: manavgat.yzyonetim.ziraatkatilim.local" -H "Authorization: Bearer %LITELLM_KEY%"
```

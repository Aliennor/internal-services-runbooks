# Katilim Dev Windows LiteLLM Test Runbook

Use this from a Windows machine or Windows Terminal session to test reachability
and LiteLLM behavior on the Katilim dev setup.

Current dev targets:

- `VM1=10.210.22.88`
- `VM2=10.210.22.89`
- `DEV_LB_IP=10.210.22.164`

Dev public hostnames:

- `manavgat.yzyonetim-dev.ziraatkatilim.local`
- `zfgasistan.yzyonetim-dev.ziraatkatilim.local`
- `aykal.yzyonetim-dev.ziraatkatilim.local`
- `mercek.yzyonetim-dev.ziraatkatilim.local`

LiteLLM exposure in the current stack:

- direct host port: `4000`
- nginx/LB hostname path: `http://manavgat.yzyonetim-dev.ziraatkatilim.local/`

Useful LiteLLM model names for dev validation:

- `gpt-oss-120b`
- `qwen3-coder-next`
- `bge-m3`
- `dots-ocr`
- `qwen3-vl`

You need a valid LiteLLM bearer key for API calls:

- usually `LITELLM_MASTER_KEY`
- get it from the dev LiteLLM `.env` on the active VM or from the approved
  secret source

## 1. If Dev DNS Is Not Ready Yet

Edit this file as Administrator:

```text
C:\Windows\System32\drivers\etc\hosts
```

Add these lines to test through the current active dev VM directly:

```text
10.210.22.88 manavgat.yzyonetim-dev.ziraatkatilim.local
10.210.22.88 zfgasistan.yzyonetim-dev.ziraatkatilim.local
10.210.22.88 aykal.yzyonetim-dev.ziraatkatilim.local
10.210.22.88 mercek.yzyonetim-dev.ziraatkatilim.local
```

If the dev LB is already routing correctly, you can map them to the LB instead:

```text
10.210.22.164 manavgat.yzyonetim-dev.ziraatkatilim.local
10.210.22.164 zfgasistan.yzyonetim-dev.ziraatkatilim.local
10.210.22.164 aykal.yzyonetim-dev.ziraatkatilim.local
10.210.22.164 mercek.yzyonetim-dev.ziraatkatilim.local
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

### CMD

```cmd
curl.exe -I --max-time 10 http://10.210.22.88:4000/
```

```cmd
curl.exe -I --max-time 10 http://10.210.22.164/
```

### PowerShell

```powershell
Test-NetConnection 10.210.22.88 -Port 4000
```

```powershell
Test-NetConnection 10.210.22.164 -Port 80
```

### Optional Telnet

```cmd
telnet 10.210.22.88 4000
```

```cmd
telnet 10.210.22.164 80
```

## 4. Raw LiteLLM API Tests Against `VM1:4000`

List models:

```cmd
curl.exe -sS http://10.210.22.88:4000/v1/models -H "Authorization: Bearer %LITELLM_KEY%"
```

Confirm useful dev models are present:

```cmd
curl.exe -sS http://10.210.22.88:4000/v1/models -H "Authorization: Bearer %LITELLM_KEY%" | findstr /I "gpt-oss-120b qwen3-coder-next bge-m3 dots-ocr qwen3-vl"
```

Chat completion test: `gpt-oss-120b`

```cmd
curl.exe -sS http://10.210.22.88:4000/v1/chat/completions -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"gpt-oss-120b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: dev-ok\"}],\"max_tokens\":16}"
```

Chat completion test: `qwen3-coder-next`

```cmd
curl.exe -sS http://10.210.22.88:4000/v1/chat/completions -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"qwen3-coder-next\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: coder-dev-ok\"}],\"max_tokens\":16}"
```

Embedding test: `bge-m3`

```cmd
curl.exe -sS http://10.210.22.88:4000/v1/embeddings -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"bge-m3\",\"input\":\"Dev embedding test\"}"
```

OCR-family probe:

```cmd
curl.exe -sS http://10.210.22.88:4000/v1/chat/completions -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"dots-ocr\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: ocr-dev-ok\"}],\"max_tokens\":16}"
```

## 5. Test Through The Final Hostname Path

```cmd
curl.exe -sS http://manavgat.yzyonetim-dev.ziraatkatilim.local/v1/models -H "Authorization: Bearer %LITELLM_KEY%"
```

```cmd
curl.exe -sS http://manavgat.yzyonetim-dev.ziraatkatilim.local/v1/chat/completions -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"gpt-oss-120b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: host-dev-ok\"}],\"max_tokens\":16}"
```

## 6. Test Through LB IP Without DNS

```cmd
curl.exe -sS http://10.210.22.164/v1/models -H "Host: manavgat.yzyonetim-dev.ziraatkatilim.local" -H "Authorization: Bearer %LITELLM_KEY%"
```

```cmd
curl.exe -sS http://10.210.22.164/v1/chat/completions -H "Host: manavgat.yzyonetim-dev.ziraatkatilim.local" -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"gpt-oss-120b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: lb-dev-ok\"}],\"max_tokens\":16}"
```

## 7. Minimal Fast Test Set

```cmd
set LITELLM_KEY=PASTE_REAL_LITELLM_MASTER_KEY_HERE
```

```cmd
curl.exe -sS http://10.210.22.88:4000/v1/models -H "Authorization: Bearer %LITELLM_KEY%"
```

```cmd
curl.exe -sS http://10.210.22.88:4000/v1/chat/completions -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"gpt-oss-120b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only: ok\"}],\"max_tokens\":16}"
```

```cmd
curl.exe -sS http://10.210.22.88:4000/v1/embeddings -H "Authorization: Bearer %LITELLM_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"bge-m3\",\"input\":\"test\"}"
```

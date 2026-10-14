# Manufacturing order-exception MCP agent

Synthetic order SO-1001: 30 ordered, 8 available, 22-unit shortage, 12-day replenishment estimate.
This reference does not connect to an ERP or send messages.

## Install (Windows PowerShell)

From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,sql,agent-workflows]"
```

## Secrets

```powershell
$secret = Read-Host "OpenAI API key" -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password.Trim()
# Repeat with ANTHROPIC_API_KEY and GOOGLE_API_KEY for the other providers.
```

Do not commit API keys.

## Run

```powershell
$demo = '.\examples\enterprise_agent_workflows\manufacturing_orders'
.\.venv\Scripts\python.exe -m unittest discover -s $demo -p 'test_*.py' -v
.\.venv\Scripts\python.exe "$demo\deterministic_demo.py"
.\.venv\Scripts\python.exe "$demo\compare_models.py" --providers openai claude gemini
.\.venv\Scripts\python.exe "$demo\approval_workflow.py"
```

Benchmark outputs under `runs/` can contain prompts and tool responses; do not publish them.

## Architecture and risk boundaries

See [ARCHITECTURE_WALKTHROUGH.md](ARCHITECTURE_WALKTHROUGH.md). The scores are smoke tests, not production security certification. An MCP tool schema does not replace server-side entitlement checks. The approval workflow demonstrates in-memory interrupt/resume only.

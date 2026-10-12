# Multi-provider agent demonstration

## Install in the existing virtual environment (PowerShell)

```powershell
cd C:\NPM\AI\enterprise-ai-patterns
.\.venv\Scripts\python.exe -m pip install -U "langchain>=1,<2" langchain-openai langchain-anthropic langchain-google-genai langchain-mcp-adapters "mcp>=1,<3" langgraph
```

## Set keys privately in the current PowerShell session

```powershell
$secret = Read-Host "OpenAI API key" -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password.Trim()
$secret = Read-Host "Claude API key" -AsSecureString
$env:ANTHROPIC_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password.Trim()
$secret = Read-Host "Gemini API key" -AsSecureString
$env:GOOGLE_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password.Trim()
Remove-Variable secret
```

## Run (from repository root)

```powershell
$demo = '.\examples\enterprise_agent_workflows\manufacturing_orders'
.\.venv\Scripts\python.exe -m unittest discover -s $demo -p 'test_*.py' -v
.\.venv\Scripts\python.exe "$demo\compare_models.py" --providers openai claude gemini
.\.venv\Scripts\python.exe "$demo\approval_workflow.py"
$env:AGENT_PROVIDER = 'claude'
.\.venv\Scripts\python.exe "$demo\langchain_agent.py"
```

The comparison skips providers without configured credentials and records JSON reports in `runs/` (untracked; **do not commit**). Provider model defaults are in `model_config.py`; set `OPENAI_AGENT_MODEL`, `CLAUDE_AGENT_MODEL`, or `GEMINI_AGENT_MODEL` to override. Confirm exact model IDs are supported by your accounts. Each LLM evaluation run consumes billable tokens.

Add `examples/enterprise_agent_workflows/manufacturing_orders/runs/` to `.gitignore`.

## What the score means

- Comparison checks are **smoke tests**, not statistically valid measures of grounding, safety, or quality.
- Tool calls and tool outputs are captured from LangChain messages. This is not a full distributed trace with individual tool latencies, MCP transport logs, or immutable auditing.
- Approval workflow uses an in-memory checkpoint and simulates the final action. It is not durable across process restart; it has no real escalation side effect and requires authenticated server-side approval before production use.
- The `mcp_server.py` exposes read-only tools and a draft-only operation. It does not expose a send action.

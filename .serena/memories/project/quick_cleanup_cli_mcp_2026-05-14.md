# Quick cleanup CLI/MCP - 2026-05-14

Additional quick/safe maintainability pass:
- Added `call_mcp_tool(app, tool_name, tool_args)` in `bobthebot/cli.py` so CLI tool execution no longer embeds JSON-RPC envelope construction in `call_tool()`.
- Simplified `call_tool()` to only resolve tool name, parse args, and delegate to `call_mcp_tool()`.
- Added CLI tests for positional `key=value` tool args, `tools` listing, and `doctor` sanity output in `tests/test_cli.py`.
- Serena diagnostics are clean for `bobthebot/cli.py` and `tests/test_cli.py`.

Shell validation remains blocked in assistant environment by bwrap namespace failure. Manual validation:
```bash
whisper-env
python -m pytest tests/test_cli.py tests/test_mcp_server.py -q
python -m radon cc bobthebot/cli.py bobthebot/mcp_server.py bobthebot/mcp_tools.py -s -a
```

Physical junk cleanup still needs to be run locally because assistant shell is blocked:
```bash
rm -rf .venv .coverage .pytest_cache .runtime bobthebot.egg-info build dist htmlcov
find . -type d -name '__pycache__' -prune -exec rm -rf {} +
find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
```
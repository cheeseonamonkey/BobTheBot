# CLI/MCP UX polish - 2026-05-14

Final quick polish pass focused on usage simplicity, UX sanity, and reducing coupling around MCP/CLI boundaries.

Changed `bobthebot/cli.py`:
- Added `COMMANDS` tuple instead of inline command list in `main()`.
- Added `tools` command to list MCP tool names/descriptions without manually sending `tools/list` JSON-RPC.
- Added `doctor` command returning dense environment/runtime sanity details: browser/chafa/Xvfb/java resolution, runtime/log/auth paths, process status, and next smoke commands.
- Fixed `observe` path to return `app.engine.observe()` directly; `BotEngine.observe()` already returns a dict.
- Split `call_tool()` responsibilities into `parse_tool_args()` and `unwrap_tool_response()`.
- `parse_tool_args()` now rejects mixing `--args` JSON and positional `key=value` args, preserving simpler CLI semantics.
- `call_tool()` now gives a better missing tool hint: run `bobthebot-run tools`.
- Render/image logic now uses `iter_render_payloads()` and `is_image_path()` instead of embedding MCP envelope parsing inside `maybe_render()`.
- Serena/Pyright diagnostics are clean for `bobthebot/cli.py` after these changes.

Existing MCP hardening remains in place:
- `bobthebot/mcp_server.py` centralizes JSON-RPC and tool response construction.
- Malformed JSON/request/tool payload paths are handled as JSON-RPC or tool-level errors without crashing the server.

Manual validation still blocked from assistant shell due bwrap namespace failure. Run locally:
```bash
whisper-env
python -m pytest tests/test_mcp_server.py tests/test_cli.py -q
python -m pytest -q
python -m radon cc bobthebot/cli.py bobthebot/mcp_server.py bobthebot/mcp_tools.py bobthebot/models.py -s -a
python -m radon mi bobthebot/cli.py bobthebot/mcp_server.py bobthebot/mcp_tools.py bobthebot/models.py -s
```

Useful UX smoke commands:
```bash
whisper-env
python -m bobthebot.cli doctor --renderer none
python -m bobthebot.cli tools --renderer none
python -m bobthebot.cli tool bob_status --renderer none
python -m bobthebot.cli tool bob_task_schema task=mining --renderer none
python -m bobthebot.cli auth-status --renderer none
```

Potential next safe refactor if metrics justify it:
- Split `bobthebot/mcp_tools.py::build_tools()` into grouped factories: runtime/task/semantic-input/auth. Do this only after radon confirms it is a meaningful hotspot, because the current flat registry is straightforward and low-risk.
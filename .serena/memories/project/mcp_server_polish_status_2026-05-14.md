# MCP server polish status - 2026-05-14

Current MCP implementation focus:
- `bobthebot/mcp_server.py` is the JSON-RPC/MCP-ish stdio server.
- `bobthebot/mcp_tools.py` owns declarative tool registration and schemas.
- `bobthebot/models.py` owns shared schema validation and payload compaction.

Recent hardening/refactor:
- `BobMcpServer.handle()` now validates request shape up front: message must be an object, `method` is required, and method must be a string. Notifications still return `None`.
- JSON-RPC result/error construction is centralized through `_result()`, `_error()`, and `_parse_error()`.
- `serve()` now catches malformed JSON and emits JSON-RPC `-32700` parse errors, then continues processing later stdin lines.
- `tools/call` parsing is centralized in `_tool_call_args()`, which validates `params`, normalizes missing/null `arguments` to `{}`, and distinguishes bad argument shape.
- Tool response serialization is centralized in `_tool_response()`. It uses `json.dumps(..., allow_nan=False)` and converts non-serializable/NaN payloads into tool-level `isError` responses instead of crashing the JSON-RPC server.
- Unknown tools now return a tool error suggesting `tools/list`.
- `Tool.handler` is typed as `Callable[[Json], Any]`, matching the server’s support for any JSON-serializable result payload.
- Shared JSON schema validation now rejects non-finite numeric values (`NaN`, `Infinity`) via `_validate_number()`.

Regression coverage added/updated in `tests/test_mcp_server.py`:
- malformed `tools/call` params/arguments
- missing tool name priority
- missing/non-string JSON-RPC method
- non-object JSON-RPC message
- stdin parse-error continuation in `serve()`
- non-object tool payloads
- non-JSON-serializable and NaN tool payloads
- non-finite number validation
- test helper now preserves falsey params like `[]` instead of coercing to `{}`
- pyright diagnostics are clean for changed MCP production files and `tests/test_mcp_server.py`

Validation blocker:
- Shell commands currently fail before Python starts due to the host wrapper: `bwrap: No permissions to create new namespace`.
- Manual validation command to run outside the blocked wrapper:
  `whisper-env; python -m radon cc bobthebot/mcp_server.py bobthebot/mcp_tools.py bobthebot/models.py -s -a; python -m radon mi bobthebot/mcp_server.py bobthebot/mcp_tools.py bobthebot/models.py -s; python -m pytest tests/test_mcp_server.py -q`

Remaining MCP cleanup candidates:
- Split `build_tools()` into smaller groups (`runtime_tools`, `task_tools`, `raw_input_tools`, `auth_tools`) if radon flags it or tool surface grows.
- Consider moving JSON-RPC protocol constants/errors into small helpers if adopting stricter MCP compatibility later.
- Broaden test helper typing if the whole test suite is type-checked, but do not overfit tests before runtime validation passes.
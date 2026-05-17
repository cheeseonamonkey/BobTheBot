# Final agent docs edition - 2026-05-17

User requested a final high-reasoning consolidation pass using Serena context to make agent docs concise, detailed, repeatable, and deterministic.

## Final docs shape
- `docs/agent-ops.md`: new shortest source of truth for future agents. Dense checklist covering hard rules, baseline setup, entrypoints, current backends, exact MCP tool names, state locations, runtime choice, isolated Bolt replay, auth handoff pattern, determinism checks, common failure modes, and update protocol.
- `docs/project-context.md`: broader architecture/context page. Now links to `agent-ops.md` first and includes agent rules for display isolation, user handoff, no secrets, and validation before doc claims.
- `docs/isolated-bolt-runelite-demo.md`: detailed live runbook for Bolt/RuneLite on `:98`; now cross-links `agent-ops.md`.
- `README.md`: now links `docs/agent-ops.md` and `docs/project-context.md`; stale command/tool/backend/credential facts were corrected in the previous pass.
- `scripts/isolated_bolt_demo.sh`: helper for `start|status|capture|watch|stop` on isolated `:98`.

## Non-negotiable facts preserved
- Use `.venv/bin/python` / `.venv/bin/bobthebot-run`; raw `python3` previously failed due missing `websockets`.
- Current Python backends are `null` and `x11-cv`; DreamBot is legacy/experimental Java bridge only unless re-registered.
- Current runtime tool names are `bob_start_runtime`, `bob_stop_runtime`, and `bob_set_backend`; stale names `bob_runtime_start`, `bob_runtime_stop`, `bob_backend_set` should not be used.
- Repo auth credentials live at `.runtime/auth/credentials.json`, plaintext JSON chmod `0600`; not `~/.config` and not encrypted.
- Bolt/Jagex demo uses `DISPLAY=:98`, Bolt `0.20.6`, `--no-sandbox`, and Bolt session state in `~/.local/share/bolt-launcher/`.
- Always set `BOBTHEBOT_DISPLAY=:98` and `--backend x11-cv` for repo CLI tools against isolated Bolt.
- Jagex Account login through standalone RuneLite failed; Bolt/Jagex Launcher compatibility is the current working path.
- CAPTCHA/Cloudflare/OTP/2FA are human handoff states. Do not automate bypasses or record secrets.
- Known live demo facts: account label seen `MyNameIsBobbbbbbbb`; OSRS display name accepted `Kaanfoxwalk`; free world `301`; reached tutorial/start area.

## Final validation
Ran after final docs pass:
```bash
bash -n scripts/isolated_bolt_demo.sh
scripts/isolated_bolt_demo.sh status
.venv/bin/python -m bobthebot.cli tools --renderer none
.venv/bin/python -m pytest -q
```
Results: script syntax OK; status reports required binaries present and demo stopped; tools command emitted JSON; tests pass `68 passed in 2.85s`.

## Working tree caveat
`bobthebot/browser.py` remains modified from prior work (`visible_buttons()` includes links). This was pre-existing in this documentation pass and was not reverted.
# CLI demo-view pass and local repair note - 2026-05-14

Attempted to add a zero-dependency visual smoke command `demo-view` to `bobthebot/cli.py`:
- `demo_view(app)` writes `.runtime/logs/demo-view.ppm`.
- `write_demo_ppm(path, width=96, height=48)` writes a deterministic binary PPM image using stdlib only.
- `is_image_path()` accepts `.ppm` so existing chafa render path can display it.
- `doctor()` next steps include `bobthebot-run demo-view`.
- `tests/test_cli.py` has tests for `demo-view` and `.ppm` render path.

Important repair issue:
- Serena's symbol replacement was used incorrectly on the top-level `COMMANDS` assignment and corrupted the top of `bobthebot/cli.py` into invalid chained tuple assignment before `main()`.
- Assistant shell/apply_patch remain blocked by `bwrap: No permissions to create new namespace`, so local raw file repair could not be executed from the tool session.
- Manual repair: replace everything from the first top-level command tuple through the final duplicate tuple before `def main()` with:

```python
COMMANDS = (
    "status",
    "start",
    "stop",
    "backends",
    "tasks",
    "tools",
    "tool",
    "doctor",
    "demo-view",
    "auth-status",
    "auth-view",
    "observe",
    "script",
    "view",
)
```

Also move `from typing import Any` up with imports if desired; leaving it below imports is valid Python once the `COMMANDS` block is repaired.

After repair, run:
```bash
whisper-env
python -m pytest tests/test_cli.py -q
python -m bobthebot.cli demo-view
python -m bobthebot.cli demo-view --renderer chafa
```

Expected UX:
- `demo-view` prints JSON with `ok: true`, `path: .runtime/logs/demo-view.ppm`, and renders a deterministic colorful test image in terminal when chafa is available and renderer is not `none`.
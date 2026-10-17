---
name: verify
description: Check a change in QuantumYoloEngine before calling it done - runs the Python engine's pytest and the web simulator's lint, typecheck, tests and build, and explains failures. Use after editing code or docs, before committing or opening a PR.
---

# Verify a change

1. Install if needed: `pip install -r requirements-dev.txt` and
   `npm --prefix web ci` (the session-start hook does both in cloud
   sessions). Then run both engines, whichever side you changed:

   ```bash
   python -m pytest
   npm --prefix web run lint && npm --prefix web run typecheck \
     && npm --prefix web run test && npm --prefix web run build
   ```

   For UI or routing changes also run `npm --prefix web run test:e2e`
   (it previews `web/dist`, so build first). In a cloud session, if
   Playwright can't find its browser, use a temporary, uncommitted config
   that sets `launchOptions.executablePath` to `/opt/pw-browsers/chromium`
   for both projects (see the portfolio guide).
2. Reading failures:
   - A parity failure (`tests/python/test_parity_fixtures.py` or
     `web/tests/unit/parity.test.ts`) means the engines disagree. If you
     changed trading logic on purpose, change the other engine to match,
     then run `python tests/parity/generate_fixtures.py` and rerun both
     sides. Revert timestamp-only fixture changes
     (`git checkout -- tests/parity/fixtures`).
   - A missing-module error for a file under `web/src/` on a clean checkout:
     check `git status --ignored`; an unanchored root `.gitignore` rule may
     be hiding it.
   - The e2e test "keyboard-only workflow can reach the start button"
     failed once in four full runs here and passed on rerun; rerun once
     before debugging it.
3. Report what ran and the result. If something could not run here, say so.

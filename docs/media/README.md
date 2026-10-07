# Demo capture

`demo.gif` records eleven actual Chromium states from the working no-key
workflow: source import, passage inspection, case review, publication, bounded
evaluation, clean/faulty results, matched comparison, and frozen source evidence.
The pauses are chosen for readability; application values are not retouched.
`demo-poster.png` is a still alternative. `demo.json` records timing and provenance.

The fictional fixture approvals use the actor
`Recorded demo (scripted fixture acceptance)`. They are not independent human
review. No paid provider, remote service or production database is used.

## Reproduce

First complete the root README's setup, including the Playwright Chromium
install. Ports 8000 and 5173 must be free. From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r scripts/requirements-media.txt
node web/scripts/capture-demo.mjs
```

On macOS/Linux, replace the Python executable with `.venv/bin/python`.
The script resolves paths from its own location, launches the API, worker and
Vite in an isolated database, checks the completed runs, captures states, encodes
the GIF, and stops its processes. Intermediate PNGs/database/manifest remain
under ignored `data/gif-capture-*` for inspection.

Pillow is only needed to encode documentation media, not to run the workbench.
The encoder verifies frame count, looping, 20–30 second timing, a size below
5 MB and decoded-frame agreement with the captured states. The GIF preserves
the 1280 × 900 browser viewport.

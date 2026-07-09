# Tauri Desktop App — Windows Design

**Date:** 2026-06-20
**Status:** Approved
**Branch:** main

---

## Goal

Wrap the existing FastAPI + Ollama stack in a Tauri v2 shell for a one-click Windows desktop experience. Users download a single `.exe` installer, run it, and AaplaManus appears in the system tray ready to use. No Docker, no Python, no terminal.

## Architecture

```
Windows installer (.exe, NSIS bundler)
└── Tauri App
    ├── WebView → http://localhost:5172
    ├── System Tray (status indicator + menu)
    └── Sidecar: aaplamanus-server.exe  ← PyInstaller bundle of app.py
        └── FastAPI + all agents + SQLite (workspace/aaplamanus.db)
```

PyInstaller compiles `app.py` and all Python dependencies into a standalone `aaplamanus-server.exe`. Tauri declares it as a sidecar binary, starts it on launch via `tauri-plugin-shell`, and kills it on quit. The WebView loads the existing HTMX UI from `http://localhost:5172`. No Docker required.

**Tech stack:** Tauri v2, Rust, `tauri-plugin-shell`, `tauri-plugin-single-instance`, PyInstaller, GitHub Actions (windows-latest runner)

---

## New Files

```
src-tauri/
├── src/main.rs                  — entry point
├── src/lib.rs                   — tray setup, sidecar lifecycle, window events
├── Cargo.toml                   — Tauri v2 + plugins
├── tauri.conf.json              — app config, sidecar declaration, window config
├── build.rs                     — required Tauri build script
├── capabilities/default.json   — Tauri v2 permissions (shell:allow-execute for sidecar)
└── icons/                       — generated from assets/ via `cargo tauri icon`
scripts/
└── build-server.ps1             — PowerShell: PyInstaller → src-tauri/binaries/
.github/workflows/
└── build.yml                    — CI: PyInstaller → cargo tauri build → GitHub Release draft
```

`src-tauri/binaries/` is gitignored. Generated at build time by `build-server.ps1`.

Sidecar binary naming convention (Tauri v2 requirement):
`src-tauri/binaries/aaplamanus-server-x86_64-pc-windows-msvc.exe`

---

## Sidecar Lifecycle

### Startup

1. Tauri app launches, creates tray icon (amber — starting)
2. Spawns `aaplamanus-server` sidecar via `tauri-plugin-shell`
3. Polls `GET http://localhost:5172/health/ollama` every 500ms, up to 30s
4. On first HTTP response (any status): tray turns green, WebView window opens to `http://localhost:5172`
5. On 30s timeout with no response: tray turns red, window shows error page with "Retry" button

The server is considered ready on any HTTP response — 200 or 503. The web UI handles the Ollama-not-running state via the existing setup wizard.

### Shutdown

1. User clicks Quit in tray
2. `sidecar_child.kill()` called
3. Wait up to 3s for process to exit
4. `app.exit(0)`

### Rust sidecar management (lib.rs outline)

```rust
// on app setup:
let child = app.shell().sidecar("aaplamanus-server")?.spawn()?;
// store child handle in Mutex<AppState>
// spawn async task polling GET /health/ollama
// on ready: show window, update tray icon to green
// on quit menu click: child.lock().kill(), app.exit(0)
```

### Single instance

`tauri-plugin-single-instance` — double-clicking the exe while running focuses the existing window instead of launching a second instance.

---

## System Tray

### Icon states

| Color | Meaning |
|-------|---------|
| Amber | Server starting |
| Green | Server running |
| Red   | Server failed or crashed |

### Tray menu

```
● AaplaManus          ← title (non-clickable)
──────────────
Open
──────────────
Quit
```

No Start/Stop in the menu. The server runs for the lifetime of the app. Quit is the only way to stop it.

---

## Window Behavior

- Hidden on startup until server is ready (avoids blank WebView)
- "Open" in tray shows and focuses the window
- Closing window (X button) hides it — does not quit or kill the server
- Window title: "AaplaManus"
- Default size: 1200×800, resizable, centered on first open

---

## Icons

Generate from source using `cargo tauri icon <source.png>`. Source image: `assets/` directory or a 512×512 PNG placeholder created during setup. Produces all Windows `.ico` sizes (16/32/48/64/128/256px).

---

## PyInstaller Build

**`scripts/build-server.ps1`:**

```powershell
pip install pyinstaller
pyinstaller app.py `
  --name aaplamanus-server `
  --onefile `
  --hidden-import app.cost_service `
  --hidden-import app.router `
  --hidden-import app.orchestrator `
  --hidden-import app.agents.research `
  --hidden-import app.agents.file `
  --hidden-import app.agents.browser `
  --hidden-import app.agents.code `
  --add-data "templates;templates" `
  --add-data "static;static" `
  --distpath src-tauri/binaries

Rename-Item src-tauri/binaries/aaplamanus-server.exe `
  aaplamanus-server-x86_64-pc-windows-msvc.exe
```

The `--add-data` flags bundle the Jinja2 templates and static assets into the executable. The `--hidden-import` flags cover dynamic imports that PyInstaller's static analysis misses.

---

## GitHub Actions CI/CD

**`.github/workflows/build.yml`:**

```yaml
on:
  push:
    tags: ['v*']
  workflow_dispatch:

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: ./scripts/build-server.ps1
      - uses: dtolnay/rust-toolchain@stable
      - uses: tauri-apps/tauri-action@v0
        with:
          tagName: ${{ github.ref_name }}
          releaseName: AaplaManus ${{ github.ref_name }}
          releaseBody: Windows installer
          releaseDraft: true
```

Triggers on version tags (`v*`) and manual dispatch. Creates a draft GitHub Release with the `.exe` installer attached.

---

## Code Signing

Not included in v1. Windows SmartScreen will warn on first run ("Windows protected your PC"). Users click "More info" → "Run anyway". Authenticode signing is a future addition when a certificate is obtained.

---

## Testing

**Local dev:** `cargo tauri dev` — runs the Tauri shell in dev mode. Requires sidecar built first (`./scripts/build-server.ps1`). Alternatively, set `"beforeDevCommand": "python app.py"` in `tauri.conf.json` so Tauri starts the server automatically during `cargo tauri dev`.

**Build verification (manual):**
1. `./scripts/build-server.ps1` — confirms PyInstaller output
2. `cargo tauri build` — confirms installer builds
3. Install and launch the resulting `.exe`, verify:
   - Tray icon appears (amber → green)
   - WebView opens to `http://localhost:5172`
   - Closing window hides app, tray remains
   - Quit from tray kills server process and exits

**Existing 53 pytest tests are unaffected** — they test the FastAPI layer directly. No new pytest tests. The CI pipeline build success is the integration test.

---

## What Is Not In Scope

- Mac support (future plan)
- Auto-start on login
- Authenticode code signing
- Ollama download/install automation from within Tauri
- In-app update mechanism

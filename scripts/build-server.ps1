Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Installing PyInstaller..."
python -m pip install "pyinstaller==6.11.0"

Write-Host "Building aaplamanus-server.exe..."
pyinstaller app.py `
    --name aaplamanus-server `
    --onefile `
    --noconfirm `
    --clean `
    --hidden-import app.cost_service `
    --hidden-import app.router `
    --hidden-import app.orchestrator `
    --hidden-import app.llm `
    --hidden-import app.logger `
    --hidden-import app.schema `
    --hidden-import app.exceptions `
    --hidden-import app.config `
    --hidden-import app.agents.research `
    --hidden-import app.agents.file `
    --hidden-import app.agents.browser `
    --hidden-import app.agents.code `
    --hidden-import app.agents.types `
    --hidden-import app.agent.base `
    --hidden-import app.agent.manus `
    --hidden-import app.agent.planning `
    --hidden-import app.agent.react `
    --hidden-import app.agent.swe `
    --hidden-import app.agent.toolcall `
    --hidden-import app.flow.base `
    --hidden-import app.flow.flow_factory `
    --hidden-import app.flow.planning `
    --hidden-import app.prompt.manus `
    --hidden-import app.prompt.planning `
    --hidden-import app.prompt.swe `
    --hidden-import app.prompt.toolcall `
    --hidden-import app.tool.base `
    --hidden-import app.tool.bash `
    --hidden-import app.tool.browser_use_tool `
    --hidden-import app.tool.create_chat_completion `
    --hidden-import app.tool.file_saver `
    --hidden-import app.tool.google_search `
    --hidden-import app.tool.planning `
    --hidden-import app.tool.python_execute `
    --hidden-import app.tool.run `
    --hidden-import app.tool.str_replace_editor `
    --hidden-import app.tool.terminate `
    --hidden-import app.tool.tool_collection `
    --add-data "templates;templates" `
    --add-data "static;static" `
    --distpath src-tauri/binaries

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# Tauri v2 sidecar naming: <name>-<arch>-<vendor>-<os>.exe
$src = "src-tauri/binaries/aaplamanus-server.exe"
$dst = "src-tauri/binaries/aaplamanus-server-x86_64-pc-windows-msvc.exe"

if (Test-Path $dst) { Remove-Item $dst }
Rename-Item -Path $src -NewName (Split-Path $dst -Leaf)

Write-Host "Sidecar binary ready: $dst"

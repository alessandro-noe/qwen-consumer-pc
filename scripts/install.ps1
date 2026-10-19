# install.ps1 - prepares this repository on this PC (downloads nothing, installs no programs).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\install.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
Write-Host "qwen-consumer-pc: setting up in $root`n"

# 1. checks
if (-not (Test-Path "llama\llama-server.exe")) { throw "Missing llama\llama-server.exe: download llama.cpp (INSTALL.md, step 2)." }
$models = @{}
$m1 = "models\flashnext_q2_0_abl\Q2_0\Qwen3.8-Flash-Next-GSQ-RCO-abliterated-Q2_0-00001-of-00002.gguf"
$m2 = "models\flashnext_q2_0\Q2_0\Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf"
if (Test-Path $m1) { $models["flashnext-uncensored"] = "Flash-Next 125B uncensored (~35 tok/s)" }
if (Test-Path $m2) { $models["flashnext-normale"] = "Flash-Next 125B normal (~39 tok/s)" }
if ($models.Count -eq 0) { throw "No model found in models\ (INSTALL.md, step 3)." }
Write-Host "Models found: $($models.Keys -join ', ')"
python -c "import mcp" 2>$null; if ($LASTEXITCODE -ne 0) { throw "Missing Python package 'mcp': pip install -r requirements.txt" }

# 2. opencode.json with this PC's paths
$p = $root -replace '\\', '/'
$entries = @{}
foreach ($k in $models.Keys) { $entries[$k] = @{ name = $models[$k]; limit = @{ context = 65536; output = 32768 } } }
$default = if ($models.ContainsKey("flashnext-uncensored")) { "flashnext-uncensored" } else { "flashnext-normale" }
$cfg = [ordered]@{
  '$schema'   = "https://opencode.ai/config.json"
  model       = "locale/$default"
  provider    = @{ locale = @{ npm = "@ai-sdk/openai-compatible"; name = "Local model (qwen-consumer-pc)";
                               options = @{ baseURL = "http://127.0.0.1:8091/v1" }; models = $entries } }
  mcp         = [ordered]@{
    kael       = @{ type = "local"; command = @("python", "$p/extras/kael_mcp.py"); enabled = $true }
    biblioteca = @{ type = "local"; command = @("python", "$p/extras/biblioteca_mcp.py"); enabled = $true } }
  instructions = @("$p/opencode/REGOLE_AGENTE.md")
  permission  = @{ skill = [ordered]@{ "*" = "deny"; "minimo" = "allow"; "adatta-skill" = "allow"; "verifica" = "allow";
                                       "cerca-prima" = "allow"; "nuovo-progetto" = "allow"; "sbloccati" = "allow" } }
}
$cfg | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 "opencode.json"
if (-not (Test-Path ".opencode")) { Copy-Item -Recurse "opencode\.opencode" ".opencode" }
Write-Host "Created opencode.json (default model: $default)."

# 3. start the proxy with Windows (optional, asks first)
$r = Read-Host "Start the proxy (smistatore) with Windows? It uses no GPU until you send a request. (y/n)"
if ($r -match '^[yYsS]') {
  $py = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
  if (-not $py) { $py = (Get-Command python.exe).Source }
  $vbs = Join-Path ([Environment]::GetFolderPath("Startup")) "qwen-consumer-pc-proxy.vbs"
  @"
' qwen-consumer-pc: starts the proxy hidden at logon. To disable: delete this file.
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "$root"
sh.Environment("PROCESS")("SMISTA_SCALATA") = "1"
sh.Environment("PROCESS")("SMISTA_NOTE") = "0"
sh.Run """$py"" proxy\smistatore.py", 0, False
"@ | Set-Content -Encoding ascii $vbs
  Start-Process wscript.exe -ArgumentList "`"$vbs`""
  Write-Host "Autostart created: $vbs (proxy started now as well)."
} else {
  Write-Host "Ok. Start the proxy manually with: scripts\start_proxy.cmd"
}
Write-Host "`nDone. Open a terminal in this folder and type: opencode"

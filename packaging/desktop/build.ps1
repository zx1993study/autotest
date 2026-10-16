param(
    [string]$Python = "python",
    [string]$Version = "0.3.10",
    [ValidateSet("core", "mobile", "mobile-web", "web", "ai-web", "full")][string]$AgentProfile = "mobile",
    [switch]$BuildAgent,
    [switch]$BuildInstaller,
    [string]$InnoSetupCompiler = "ISCC.exe"
)
$ErrorActionPreference = "Stop"
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Invalid package version" }
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
& $Python -m PyInstaller --noconfirm --clean --distpath (Join-Path $PSScriptRoot "dist") --workpath (Join-Path $PSScriptRoot "build") (Join-Path $PSScriptRoot "AutotestPlatform.spec")
if ($LASTEXITCODE -ne 0) { throw "Desktop build failed" }
if ($BuildAgent) {
    $env:AUTOTEST_AGENT_PROFILE = $AgentProfile
    & $Python -m PyInstaller --noconfirm --clean --distpath (Join-Path $PSScriptRoot "dist") --workpath (Join-Path $PSScriptRoot "build-agent") (Join-Path $Root "agent\AutotestAgentSplit.spec")
    if ($LASTEXITCODE -ne 0) { throw "Agent build failed" }
    Copy-Item -LiteralPath (Join-Path $Root "agent\windows\agent-config.example.json") -Destination (Join-Path $PSScriptRoot "dist\AutotestAgent\config.example.json") -Force
    $ConfigPath = Join-Path $PSScriptRoot "dist\AutotestAgent\config.example.json"
    $Config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    $Config | Add-Member -NotePropertyName version -NotePropertyValue $Version -Force
    if ($AgentProfile -eq "mobile-web") {
        $Config.plugins = @("mobile", "web")
    }
    [System.IO.File]::WriteAllText($ConfigPath, ($Config | ConvertTo-Json -Depth 10), [System.Text.UTF8Encoding]::new($false))
}
if ($BuildInstaller) {
    & $InnoSetupCompiler "/DMyAppVersion=$Version" (Join-Path $PSScriptRoot "AutotestPlatform.iss")
    if ($LASTEXITCODE -ne 0) { throw "Installer build failed" }
}

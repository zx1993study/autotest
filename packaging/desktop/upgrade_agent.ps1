param(
    [string]$InstallRoot = "D:\AutotestPlatform",
    [string]$Source = (Join-Path $PSScriptRoot "dist\AutotestAgent")
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath $InstallRoot).Path.TrimEnd('\')
$Target = [System.IO.Path]::GetFullPath((Join-Path $Root "agent"))
if (-not $Target.StartsWith($Root + '\', [System.StringComparison]::OrdinalIgnoreCase)) { throw "Invalid Agent target" }
$Source = (Resolve-Path -LiteralPath $Source).Path
$Exe = Join-Path $Target "AutotestAgent.exe"
if (-not (Test-Path -LiteralPath (Join-Path $Source "AutotestAgent.exe"))) { throw "Build the mobile-web Agent first" }
$BuildConfig = Get-Content -LiteralPath (Join-Path $Source "config.example.json") -Raw | ConvertFrom-Json
if ($BuildConfig.version -notmatch '^\d+\.\d+\.\d+$') { throw "Invalid built Agent version" }
if (@($BuildConfig.plugins).Count -ne 2 -or 'mobile' -notin $BuildConfig.plugins -or 'web' -notin $BuildConfig.plugins) { throw "Upgrade requires a mobile-web Agent build" }
$ConfigPath = Join-Path $env:LOCALAPPDATA "AutotestAgent\config.json"
$Config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$Hash = [System.Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData([System.Text.Encoding]::UTF8.GetBytes($Config.node_key))).ToLower().Substring(0, 24)
$Runtime = Join-Path $env:LOCALAPPDATA "AutotestAgent\runtime\$Hash.json"
$StopFile = [System.IO.Path]::ChangeExtension($Runtime, ".stop")
if (Test-Path -LiteralPath $Runtime) {
    $State = Get-Content -LiteralPath $Runtime -Raw | ConvertFrom-Json
    if ($State.status -in @("busy", "uploading")) { throw "Agent is busy; finish the current task before upgrading" }
}
$Processes = @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $Exe })
# Stop requests prevent new claims; allow the worker to finish its current network call.
[System.IO.File]::WriteAllText($StopFile, "", [System.Text.UTF8Encoding]::new($false))
foreach ($Process in $Processes | Where-Object { $_.CommandLine -match '--tray' }) { Stop-Process -Id $Process.ProcessId }
$Deadline = [DateTime]::UtcNow.AddSeconds(45)
do {
    $Workers = @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $Exe })
    if ($Workers.Count -eq 0) { break }
    Start-Sleep -Seconds 1
} while ([DateTime]::UtcNow -lt $Deadline)
if ($Workers.Count -gt 0) { throw "Worker has not safely stopped; no files were replaced" }
$Backup = Join-Path $Root ("upgrade-backups\" + (Get-Date -Format "yyyyMMdd-HHmmss") + "-mobile-web")
New-Item -ItemType Directory -Path $Backup | Out-Null
Copy-Item -LiteralPath $Target -Destination (Join-Path $Backup "agent") -Recurse
Copy-Item -LiteralPath $ConfigPath -Destination (Join-Path $Backup "agent-config.json")
try {
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $Target -Recurse -Force }
    $Config.plugins = @("mobile", "web")
    $Config.version = $BuildConfig.version
    $Temporary = $ConfigPath + ".new"
    [System.IO.File]::WriteAllText($Temporary, ($Config | ConvertTo-Json -Depth 20), [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $Temporary -Destination $ConfigPath -Force
    & $Exe --check-runtime
    if ($LASTEXITCODE -ne 0) { throw "Installed runtime check failed" }
} catch {
    Get-ChildItem -LiteralPath (Join-Path $Backup "agent") -Force | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $Target -Recurse -Force }
    Copy-Item -LiteralPath (Join-Path $Backup "agent-config.json") -Destination $ConfigPath -Force
    throw
} finally {
    Start-Process -FilePath $Exe -ArgumentList '--tray' -WorkingDirectory $Target -WindowStyle Hidden | Out-Null
}
Write-Output "Agent upgraded; node credentials, mobile data and artifacts preserved. Backup: $Backup"

param([string]$Version = (Get-Date -Format 'yyyyMMdd-HHmmss'))
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not (Test-Path -LiteralPath (Join-Path $Root 'frontend\dist\index.html'))) {
    throw 'Build frontend before creating the server release.'
}
if ($Version -notmatch '^[a-zA-Z0-9.-]+$') { throw 'Invalid version' }
$Output = Join-Path $PSScriptRoot 'dist'
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$Archive = Join-Path $Output "AutotestPlatform-server-$Version.tar.gz"
$Files = @('backend/app','backend/migrations','backend/alembic.ini','backend/requirements.txt','web_automation/pyproject.toml','web_automation/src','frontend/dist','scripts/migrate_runtime_storage.py','packaging/server/run.py','packaging/server/verify_generation_model.py','packaging/server/verify_app_exploration_model.py','packaging/server/prepare_upgrade.py','packaging/server/backup_release.py','packaging/server/merge_runtime.py','packaging/server/configure_nginx.py','packaging/server/switch_release.py','packaging/server/autotest-platform.service','packaging/server/nginx-location.conf','docs/remote-desktop-agent.md','docs/business-ai-generation.md','docs/web-function-testing.md','docs/app-live-generation.md')
foreach ($File in $Files) {
    if (-not (Test-Path -LiteralPath (Join-Path $Root $File))) { throw "Missing release file: $File" }
}
$StagingArchive = "$Archive.partial"
& tar.exe --exclude='__pycache__' --exclude='*.pyc' --exclude='storage' --exclude='.env*' -czf $StagingArchive -C $Root @Files
if ($LASTEXITCODE -ne 0) { throw 'Server release build failed' }
Move-Item -LiteralPath $StagingArchive -Destination $Archive -Force
Write-Output $Archive
Get-FileHash -LiteralPath $Archive -Algorithm SHA256 | Select-Object Algorithm,Hash

param([string]$InstallRoot = 'D:\AutotestPlatform')

$ErrorActionPreference = 'Stop'
$expectedRoot = [IO.Path]::GetFullPath('D:\AutotestPlatform').TrimEnd('\')
$root = (Resolve-Path -LiteralPath $InstallRoot).Path.TrimEnd('\')
if ($root -ne $expectedRoot) { throw 'Unexpected installation directory.' }
$source = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\packaging\standalone\dist\AutotestPlatform')).Path
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$app = Join-Path $root 'app'
$staged = Join-Path $root "app.next-$stamp"
$backup = Join-Path $root "app.previous-$stamp"
$exe = Join-Path $app 'AutotestPlatform.exe'

foreach ($path in @($app, $staged, $backup)) {
    $absolute = [IO.Path]::GetFullPath($path)
    if ([IO.Path]::GetDirectoryName($absolute) -ne $root) { throw 'Unsafe deployment path.' }
}
foreach ($path in @('D:\', $root, $app, $source)) {
    if ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'Deployment directory cannot be a reparse point.'
    }
}
$links = Get-ChildItem -LiteralPath $app,$source -Recurse -Force |
    Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }
if ($links) { throw 'Deployment content cannot contain reparse points.' }

$preserved = @{}
foreach ($relative in @('config.json', 'secret.key', 'app\config.json')) {
    $file = Join-Path $root $relative
    if (Test-Path -LiteralPath $file) { $preserved[$relative] = (Get-FileHash -LiteralPath $file).Hash }
}
Copy-Item -LiteralPath $source -Destination $staged -Recurse
if (Test-Path -LiteralPath (Join-Path $app 'config.json')) {
    Copy-Item -LiteralPath (Join-Path $app 'config.json') -Destination (Join-Path $staged 'config.json')
}
if ((Get-FileHash -LiteralPath (Join-Path $source 'AutotestPlatform.exe')).Hash -ne
    (Get-FileHash -LiteralPath (Join-Path $staged 'AutotestPlatform.exe')).Hash) { throw 'Staging checksum mismatch.' }

$running = @(Get-CimInstance Win32_Process -Filter "Name='AutotestPlatform.exe'" |
    Where-Object { $_.ExecutablePath -eq $exe })
foreach ($item in $running) {
    $process = Get-Process -Id $item.ProcessId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $process.Id
        if (-not $process.WaitForExit(15000)) { throw 'Application did not exit.' }
    }
}
Start-Sleep -Seconds 2
Move-Item -LiteralPath $app -Destination $backup
try {
    Move-Item -LiteralPath $staged -Destination $app
} catch {
    Move-Item -LiteralPath $backup -Destination $app
    throw
}
foreach ($relative in $preserved.Keys) {
    if ((Get-FileHash -LiteralPath (Join-Path $root $relative)).Hash -ne $preserved[$relative]) {
        throw "Preserved configuration changed: $relative"
    }
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '..\packaging\standalone\README.md') -Destination (Join-Path $root 'README-standalone.md') -Force
$timer = [Diagnostics.Stopwatch]::StartNew()
$process = Start-Process -FilePath $exe -WorkingDirectory $app -WindowStyle Normal -PassThru
$result = [ordered]@{pid=$process.Id;backup=$backup;configuration_preserved=$true;ready=$false}
for ($attempt = 0; $attempt -lt 90; $attempt++) {
    if ($process.HasExited) { throw 'New application exited before becoming ready.' }
    try {
        $runtime = Get-Content -LiteralPath (Join-Path $root 'runtime.json') -Raw | ConvertFrom-Json
        if ($runtime.pid -eq $process.Id) {
            $response = Invoke-WebRequest -Uri ($runtime.url.TrimEnd('/') + '/api/v1/auth/bootstrap') -UseBasicParsing -TimeoutSec 2
            $body = $response.Content | ConvertFrom-Json
            if ($response.StatusCode -eq 200 -and $body.code -eq 0) {
                $result.ready=$true
                $result.url=$runtime.url
                $result.http_ready_ms=$timer.ElapsedMilliseconds
                break
            }
        }
    } catch {}
    Start-Sleep -Milliseconds 500
}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'startup-deployment-result.json') -Encoding UTF8
$result | ConvertTo-Json
if (-not $result.ready) { throw 'New application readiness timeout; backup retained.' }

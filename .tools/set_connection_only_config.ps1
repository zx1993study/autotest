$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath 'D:\AutotestPlatform').Path.TrimEnd('\')
if ($root -ne 'D:\AutotestPlatform') { throw 'Unexpected installation directory.' }
foreach ($relative in @('config.json', 'app\config.json')) {
    $path = Join-Path $root $relative
    if ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'Configuration cannot be a reparse point.'
    }
    $config = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    $config | Add-Member -MemberType NoteProperty -Name auto_create_schema -Value $false -Force
    [IO.File]::WriteAllText($path, ($config | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
}
'Installed configuration: connection-only startup enabled; other settings retained.'

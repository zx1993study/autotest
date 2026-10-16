param(
    [string]$InnoSetupCompiler = "ISCC.exe"
)

$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "AutotestAgent.iss"
$compiler = Get-Command $InnoSetupCompiler -ErrorAction SilentlyContinue

if (-not $compiler) {
    throw "未找到 Inno Setup 编译器。请安装 Inno Setup 后重试，或使用 install.ps1 进行当前用户安装。"
}

& $compiler.Source $script

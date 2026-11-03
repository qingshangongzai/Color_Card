# 构建单实例启动器（MSVC）
#
# 用法：
#   pwsh -File launcher/build.ps1 -MainExeName "Color Card Portable.exe" -OutputPath "dist\Color Card Launcher.exe"
#
# 依赖本机或 CI 的 Visual Studio（含 C++ 生成工具），通过 vswhere 定位。

param(
    [Parameter(Mandatory = $true)]
    [string]$MainExeName,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$launcherDir = $PSScriptRoot
$buildDir = Join-Path $launcherDir 'build'
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

$configHeader = Join-Path $launcherDir 'launcher_config.h'
Set-Content -Path $configHeader -Encoding utf8 -Value @"
#pragma once
#define MAIN_EXE_NAME L"$MainExeName"
"@

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path $vswhere)) {
    throw "vswhere 不存在：$vswhere"
}
$vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsPath) {
    throw '未找到带 C++ 生成工具的 Visual Studio'
}
$vcvars = Join-Path $vsPath 'VC\Auxiliary\Build\vcvars64.bat'

$outputFull = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath))
$batPath = Join-Path $buildDir 'build.bat'
# 路径经环境变量传给批处理，避免非 ASCII 路径在 ASCII 编码的 .bat 中被替换成问号
$env:LAUNCHER_VCVARS = $vcvars
$env:LAUNCHER_OUTPUT = $outputFull
$batContent = @"
@echo off
call "%LAUNCHER_VCVARS%" || exit /b 1
cd /d "%~dp0.."
rc /nologo /fo build\launcher.res launcher.rc || exit /b 1
cl /nologo /O2 /utf-8 /W4 /Fo:build\launcher.obj launcher.c /Fe:"%LAUNCHER_OUTPUT%" /link /SUBSYSTEM:WINDOWS user32.lib shell32.lib build\launcher.res || exit /b 1
"@
Set-Content -Path $batPath -Encoding ascii -Value ($batContent -replace "`n", "`r`n")

cmd /c "`"$batPath`""
if ($LASTEXITCODE -ne 0) {
    throw "启动器编译失败，退出码 $LASTEXITCODE"
}

Write-Host "启动器已生成: $outputFull"

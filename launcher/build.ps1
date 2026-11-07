# 构建便携版根目录启动器（MSVC）
#
# 本脚本含中文常量，须保存为 UTF-8 with BOM：Windows PowerShell 5.1 对无 BOM 的脚本按 ANSI 解析，中文会乱码
# 用法：
#   pwsh -File launcher/build.ps1 -OutputPath "Color Card.exe"
#
# 依赖本机或 CI 的 Visual Studio（含 C++ 生成工具），通过 vswhere 定位。

param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$launcherDir = $PSScriptRoot
$buildDir = Join-Path $launcherDir 'build'
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

# 版本与版权信息和 CI 打包同源：读根目录 version.txt（唯一真源），写入 VERSIONINFO 资源
# -Encoding utf8 显式声明读取编码：该文件无 BOM，Windows PowerShell 默认按 ANSI 读取会把中文读乱
$versionLines = Get-Content (Join-Path (Split-Path $launcherDir -Parent) 'version.txt') -Encoding utf8
$fileVersion = $versionLines[1].Trim()
$productVersion = $versionLines[2].Trim()
$companyName = $versionLines[3].Trim()
$copyright = $versionLines[4].Trim()
$appName = $versionLines[5].Trim()
# FILEVERSION / PRODUCTVERSION 需要「四段数字逗号分隔」的格式，段数不足时补 0
$fileVersionQuad = ((($fileVersion -split '\.') + @('0', '0', '0', '0'))[0..3] -join ',')
$productVersionQuad = ((($productVersion -split '\.') + @('0', '0', '0', '0'))[0..3] -join ',')

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
$launcherFileName = [System.IO.Path]::GetFileName($outputFull)
$launcherInternalName = [System.IO.Path]::GetFileNameWithoutExtension($outputFull)

# 版本资源以 UTF-16（带 BOM）落盘：rc.exe 按 BOM 识别编码，
# 在默认 ANSI 代码页不含中文的英文系统 runner 上编译，中文与 © 才不会乱码
$versionRcPath = Join-Path $buildDir 'launcher_version.rc'
Set-Content -Path $versionRcPath -Encoding unicode -Value @"
1 VERSIONINFO
FILEVERSION $fileVersionQuad
PRODUCTVERSION $productVersionQuad
FILEFLAGSMASK 0x3fL
FILEFLAGS 0x0L
FILEOS 0x40004L
FILETYPE 0x1L
FILESUBTYPE 0x0L
BEGIN
    BLOCK "StringFileInfo"
    BEGIN
        BLOCK "080404b0"
        BEGIN
            VALUE "CompanyName",      "$companyName"
            VALUE "FileDescription",  "取色卡 - Color Card (Launcher)"
            VALUE "FileVersion",      "$fileVersion"
            VALUE "InternalName",     "$launcherInternalName"
            VALUE "LegalCopyright",   "$copyright"
            VALUE "OriginalFilename", "$launcherFileName"
            VALUE "ProductName",      "$appName"
            VALUE "ProductVersion",   "$productVersion"
        END
    END
    BLOCK "VarFileInfo"
    BEGIN
        VALUE "Translation", 0x0804, 1200
    END
END
"@

$batPath = Join-Path $buildDir 'build.bat'
# 路径经环境变量传给批处理，避免非 ASCII 路径在 ASCII 编码的 .bat 中被替换成问号
$env:LAUNCHER_VCVARS = $vcvars
$env:LAUNCHER_OUTPUT = $outputFull
$batContent = @"
@echo off
call "%LAUNCHER_VCVARS%" || exit /b 1
cd /d "%~dp0.."
rc /nologo /fo build\launcher.res launcher.rc || exit /b 1
rc /nologo /fo build\launcher_version.res build\launcher_version.rc || exit /b 1
cl /nologo /O2 /utf-8 /W4 /Fo:build\launcher.obj launcher.c /Fe:"%LAUNCHER_OUTPUT%" /link /SUBSYSTEM:WINDOWS user32.lib shell32.lib build\launcher.res build\launcher_version.res || exit /b 1
"@
Set-Content -Path $batPath -Encoding ascii -Value ($batContent -replace "`n", "`r`n")

cmd /c "`"$batPath`""
if ($LASTEXITCODE -ne 0) {
    throw "启动器编译失败，退出码 $LASTEXITCODE"
}

Write-Host "启动器已生成: $outputFull"

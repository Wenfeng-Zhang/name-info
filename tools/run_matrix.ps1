<#
.SYNOPSIS
    在每个可用的 CPython 解释器上运行测试套件。

.DESCRIPTION
    为 .venv37 / .venv39 / .venv310 / .venv311 创建（或复用）项目内虚拟环境，
    然后在每个环境中执行 tests 目录下的 unittest 套件。
    测试只依赖标准库，因此本脚本不会安装任何第三方包。

    为了让虚拟环境里的 pip 也能正常使用（例如后续手动安装 wheel、pytest），
    脚本会把这台机器上更好访问的镜像写进 venv 根目录的 pip.ini。

.PARAMETER Recreate
    先删除已有的 .venvXX 目录再重建。

.PARAMETER IndexUrl
    写入 venv 的 pip index-url，默认使用清华大学镜像站；
    传空字符串则不写入，并删除已有的 pip.ini。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools/run_matrix.ps1
    powershell -ExecutionPolicy Bypass -File tools/run_matrix.ps1 -Recreate
    powershell -ExecutionPolicy Bypass -File tools/run_matrix.ps1 -IndexUrl ''
#>
[CmdletBinding()]
param(
    [switch]$Recreate,

    [string]$IndexUrl = 'https://pypi.tuna.tsinghua.edu.cn/simple'
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$testsDirectory = Join-Path $root 'tests'

# 环境目录名 -> 解释器路径。按解释器版本从低到高排列。
$interpreters = [ordered]@{
    '.venv37'  = 'C:\Python37\python.exe'
    '.venv39'  = 'C:\Python39\python.exe'
    '.venv310' = 'C:\Python310\python.exe'
    '.venv311' = 'C:\Python311\python.exe'
}

$env:PYTHONPATH = $root
$results = @()

foreach ($name in $interpreters.Keys) {
    $basePython = $interpreters[$name]
    $venvDirectory = Join-Path $root $name
    $venvPython = Join-Path $venvDirectory 'Scripts\python.exe'

    if (-not (Test-Path $basePython)) {
        Write-Warning "$name : interpreter not found, skipping ($basePython)"
        $results += [pscustomobject]@{
            Environment = $name; Version = '-'; Result = 'missing'
        }
        continue
    }

    if ($Recreate -and (Test-Path $venvDirectory)) {
        Remove-Item -Recurse -Force $venvDirectory
    }

    if (-not (Test-Path $venvPython)) {
        Write-Host "creating $name ..." -ForegroundColor Cyan
        & $basePython -m venv $venvDirectory
        if ($LASTEXITCODE -ne 0) {
            $results += [pscustomobject]@{
                Environment = $name; Version = '-'; Result = "venv failed ($LASTEXITCODE)"
            }
            continue
        }
    }

    # pip 源：写进 venv 根目录的 pip.ini，venv 重建后由本脚本恢复。
    $pipIni = Join-Path $venvDirectory 'pip.ini'
    if ($IndexUrl) {
        Set-Content -LiteralPath $pipIni -Encoding ASCII -Value @(
            '[global]'
            "index-url = $IndexUrl"
        )
    } else {
        Remove-Item -LiteralPath $pipIni -ErrorAction SilentlyContinue
    }

    $version = (& $venvPython -c "import sys; print(sys.version.split()[0])")
    Write-Host "=== $name (Python $version) ===" -ForegroundColor Cyan
    & $venvPython -m unittest discover -s $testsDirectory -v
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        $outcome = 'pass'
    } else {
        $outcome = "fail (exit $exitCode)"
    }

    $results += [pscustomobject]@{
        Environment = $name
        Version     = $version
        Result      = $outcome
    }
}

Write-Host ''
$results | Format-Table -AutoSize

$failed = $results | Where-Object { $_.Result -ne 'pass' }
if ($failed) {
    Write-Host ("{0} of {1} environment(s) did not pass." -f $failed.Count, $results.Count) -ForegroundColor Red
    exit 1
}

Write-Host ("all {0} environment(s) passed." -f $results.Count) -ForegroundColor Green

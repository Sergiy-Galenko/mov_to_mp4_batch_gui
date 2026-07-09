param(
    [ValidateSet("run", "build")]
    [string]$Mode = "run",
    [switch]$SkipDependencyInstall,
    [switch]$SkipDesktopExe,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArgs
)

$ErrorActionPreference = "Stop"

$RequiredMajor = 3
$RequiredMinor = 12
$InstallWingetId = "Python.Python.3.13"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RuntimeRequirements = Join-Path $ProjectRoot "requirements.txt"
$DevRequirements = Join-Path $ProjectRoot "requirements-dev.txt"
$DistExe = Join-Path $ProjectRoot "dist\MediaConverter.exe"

function Update-SessionPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = @($machinePath, $userPath, $env:Path) -join ";"
}

function Test-PythonCommand {
    param(
        [string]$Exe,
        [string[]]$BaseArgs = @()
    )

    if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) {
        return $null
    }

    $versionCheck = "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'); raise SystemExit(0 if sys.version_info >= ($RequiredMajor, $RequiredMinor) else 1)"
    $versionText = & $Exe @BaseArgs -c $versionCheck 2>$null
    if ($LASTEXITCODE -eq 0) {
        return [pscustomobject]@{
            Exe     = $Exe
            Args    = $BaseArgs
            Display = (@($Exe) + $BaseArgs) -join " "
            Version = ($versionText | Select-Object -First 1)
        }
    }

    return $null
}

function Find-CompatiblePython {
    $candidates = @(
        @{ Exe = "py"; Args = @("-3.13") },
        @{ Exe = "py"; Args = @("-3.12") },
        @{ Exe = "python"; Args = @() },
        @{ Exe = "python3"; Args = @() },
        @{ Exe = "py"; Args = @("-3") }
    )

    foreach ($candidate in $candidates) {
        $python = Test-PythonCommand -Exe $candidate.Exe -BaseArgs ([string[]]$candidate.Args)
        if ($null -ne $python) {
            return $python
        }
    }

    return $null
}

function Install-CompatiblePython {
    if (-not (Get-Command "winget" -ErrorAction SilentlyContinue)) {
        throw "Python $RequiredMajor.$RequiredMinor+ is required, and winget was not found. Install Python manually from https://www.python.org/downloads/windows/."
    }

    Write-Host "Python $RequiredMajor.$RequiredMinor+ was not found. Installing $InstallWingetId with winget..."
    & winget install --id $InstallWingetId --source winget --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "winget install failed; trying winget upgrade for $InstallWingetId..."
        & winget upgrade --id $InstallWingetId --source winget --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "Could not install or upgrade Python with winget."
        }
    }

    Update-SessionPath
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)]$Python,
        [string[]]$Arguments
    )

    & $Python.Exe @($Python.Args) @Arguments
}

function Ensure-CompatiblePython {
    Update-SessionPath
    $python = Find-CompatiblePython
    if ($null -ne $python) {
        Write-Host "Using Python $($python.Version): $($python.Display)"
        return $python
    }

    Install-CompatiblePython
    $python = Find-CompatiblePython
    if ($null -eq $python) {
        throw "Python $RequiredMajor.$RequiredMinor+ was installed, but this shell cannot find it. Open a new terminal and run this script again."
    }

    Write-Host "Using Python $($python.Version): $($python.Display)"
    return $python
}

function Install-Requirements {
    param([Parameter(Mandatory = $true)]$Python)

    if ($SkipDependencyInstall -or $env:MEDIA_CONVERTER_SKIP_DEP_BOOTSTRAP -in @("1", "true", "yes")) {
        Write-Host "Skipping Python package installation."
        return
    }

    if ($Mode -eq "build") {
        Invoke-Python $Python @("-m", "pip", "install", "-r", $RuntimeRequirements, "-r", $DevRequirements)
    }
    else {
        Invoke-Python $Python @("-m", "pip", "install", "-r", $RuntimeRequirements)
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Python package installation failed."
    }
}

function Install-BuildRequirements {
    param([Parameter(Mandatory = $true)]$Python)

    if ($SkipDependencyInstall -or $env:MEDIA_CONVERTER_SKIP_DEP_BOOTSTRAP -in @("1", "true", "yes")) {
        Write-Host "Skipping build dependency installation."
        return
    }

    Invoke-Python $Python @("-m", "pip", "install", "-r", $RuntimeRequirements, "-r", $DevRequirements)
    if ($LASTEXITCODE -ne 0) {
        throw "Python build dependency installation failed."
    }
}

function Get-DesktopPath {
    $desktop = [Environment]::GetFolderPath("Desktop")
    if ([string]::IsNullOrWhiteSpace($desktop)) {
        throw "Could not resolve the Windows Desktop path."
    }
    return $desktop
}

function Get-SourceNewestWriteTimeUtc {
    $excludedDirs = @(
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "dist",
        "build\media_converter"
    )
    $allowedExtensions = @(".py", ".ps1", ".cmd", ".qml", ".json", ".toml", ".txt", ".md", ".png", ".spec")
    $rootPrefix = $ProjectRoot.TrimEnd("\") + "\"
    $newest = (Get-Item -LiteralPath (Join-Path $ProjectRoot "main.py")).LastWriteTimeUtc

    Get-ChildItem -LiteralPath $ProjectRoot -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $relative = $_.FullName.Substring($rootPrefix.Length)
            foreach ($dir in $excludedDirs) {
                if ($relative -eq $dir -or $relative.StartsWith($dir + "\")) {
                    return $false
                }
            }
            return $allowedExtensions -contains $_.Extension.ToLowerInvariant()
        } |
        ForEach-Object {
            if ($_.LastWriteTimeUtc -gt $newest) {
                $newest = $_.LastWriteTimeUtc
            }
        }

    return $newest
}

function Test-NeedsDesktopBuild {
    if (-not (Test-Path -LiteralPath $DistExe)) {
        return $true
    }

    $sourceNewest = Get-SourceNewestWriteTimeUtc
    $distTime = (Get-Item -LiteralPath $DistExe).LastWriteTimeUtc
    return $distTime -lt $sourceNewest
}

function Ensure-DesktopExe {
    param([Parameter(Mandatory = $true)]$Python)

    if ($SkipDesktopExe -or $env:MEDIA_CONVERTER_SKIP_DESKTOP_EXE -in @("1", "true", "yes")) {
        Write-Host "Skipping Desktop executable creation."
        return
    }

    $desktopExe = Join-Path (Get-DesktopPath) "MediaConverter.exe"
    $needsBuild = Test-NeedsDesktopBuild
    if ($needsBuild) {
        Write-Host "Desktop executable is missing or stale. Building MediaConverter.exe..."
        Install-BuildRequirements $Python
        Push-Location $ProjectRoot
        try {
            Invoke-Python $Python @("scripts/build_pyinstaller.py")
            if ($LASTEXITCODE -ne 0) {
                throw "PyInstaller build failed."
            }
        }
        finally {
            Pop-Location
        }
    }

    if (-not (Test-Path -LiteralPath $DistExe)) {
        throw "Build finished, but $DistExe was not created."
    }

    $copyNeeded = -not (Test-Path -LiteralPath $desktopExe)
    if (-not $copyNeeded) {
        $copyNeeded = (Get-Item -LiteralPath $desktopExe).LastWriteTimeUtc -lt (Get-Item -LiteralPath $DistExe).LastWriteTimeUtc
    }

    if ($copyNeeded) {
        Copy-Item -LiteralPath $DistExe -Destination $desktopExe -Force
        Write-Host "Desktop executable ready: $desktopExe"
    }
    else {
        Write-Host "Desktop executable is up to date: $desktopExe"
    }
}

$python = Ensure-CompatiblePython
Install-Requirements $python

if ($Mode -eq "run") {
    Ensure-DesktopExe $python
}

Push-Location $ProjectRoot
try {
    if ($Mode -eq "build") {
        Invoke-Python $python @("scripts/build_pyinstaller.py")
        if ($LASTEXITCODE -eq 0 -and -not ($SkipDesktopExe -or $env:MEDIA_CONVERTER_SKIP_DESKTOP_EXE -in @("1", "true", "yes"))) {
            $desktopExe = Join-Path (Get-DesktopPath) "MediaConverter.exe"
            Copy-Item -LiteralPath $DistExe -Destination $desktopExe -Force
            Write-Host "Desktop executable ready: $desktopExe"
        }
    }
    else {
        $runArgs = @("main.py") + $AppArgs
        Invoke-Python $python $runArgs
    }

    exit $LASTEXITCODE
}
finally {
    Pop-Location
}

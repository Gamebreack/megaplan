# .SYNOPSIS
#    Bootstrap a project with the Megaplan framework (Windows version).
# .DESCRIPTION
#    Mirrors scripts/bootstrap.py for Windows users. Downloads the latest
#    framework release, lays out files into the project, installs the
#    pre-commit hook, and runs a self-test.
# .PARAMETER Ref
#    Pin a specific version (tag like v2.0.0, or branch like main). Default: latest release tag.
# .PARAMETER ProjectDir
#    Project directory to install into. Default: current directory.
# .PARAMETER WithWiki
#    Also lay out the opt-in AI wiki templates.
# .PARAMETER Force
#    Overwrite existing files.
# .PARAMETER FromLocal
#    Use a local path as the framework source (for development).
# .PARAMETER SkipHook
#    Skip the pre-commit hook install.
# .PARAMETER SkipSelfTest
#    Skip the self-test at the end.
# .EXAMPLE
#    irm https://raw.githubusercontent.com/Gamebreack/megaplan/main/scripts/bootstrap.ps1 | iex
# .EXAMPLE
#    $Ref = "v2.0.0"; irm https://raw.githubusercontent.com/Gamebreack/megaplan/main/scripts/bootstrap.ps1 | iex

param(
    [string]$Ref = "",
    [string]$ProjectDir = (Get-Location).Path,
    [switch]$WithWiki,
    [switch]$Force,
    [string]$FromLocal = "",
    [switch]$SkipHook,
    [switch]$SkipSelfTest
)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

$RepoOwner = "Gamebreack"
$RepoName = "megaplan"
$ApiUrl = "https://api.github.com/repos/$RepoOwner/$RepoName/releases/latest"
$TarballTagUrl = "https://github.com/$RepoOwner/$RepoName/archive/refs/tags/{0}.tar.gz"
$TarballBranchUrl = "https://github.com/$RepoOwner/$RepoName/archive/refs/heads/{0}.tar.gz"

# Framework file layout: source path (in framework repo) -> destination path (in user project)
$Layout = @{
    "AGENTS.md"                        = "AGENTS.md"
    "docs/methodology.md"              = "docs/megaplan/methodology.md"
    "templates/megaplan.md"            = "docs/megaplan/megaplan.md"
    "templates/backlog.md"             = "docs/megaplan/backlog.md"
    "templates/glossary.md"            = "docs/megaplan/glossary.md"
    "templates/backlog-item.md"        = "docs/megaplan/backlog-items/_template.md"
    "templates/adr.md"                 = "docs/megaplan/adr/_template.md"
    "skills/megaplan/SKILL.md"         = "SKILL.md"
}

# Wiki layout (only laid out with -WithWiki)
$WikiLayout = @{
    "templates/wiki/INDEX.md"          = "docs/megaplan/wiki/INDEX.md"
    "templates/wiki/architecture.md"   = "docs/megaplan/wiki/architecture.md"
    "templates/wiki/contract.md"       = "docs/megaplan/wiki/contract.md"
    "templates/wiki/decision.md"       = "docs/megaplan/wiki/decision.md"
    "templates/wiki/notes.md"          = "docs/megaplan/wiki/notes.md"
}

# Framework scripts (all go to scripts/megaplan/ in the user project)
$Scripts = @(
    "_mdparse.py", "_wiki_map.py", "compile_spec.py",
    "validate_backlog.py", "validate_wiki.py", "verify_workflow.py",
    "ingest_wiki.py", "setup_hooks.py"
)

# Path rewrites: applied in descending-from-length order during file copy
$PathRewrites = @(
    @{ From = "scripts/"; To = "scripts/megaplan/" }
    @{ From = "docs/methodology.md"; To = "docs/megaplan/methodology.md" }
    @{ From = "templates/megaplan.md"; To = "docs/megaplan/megaplan.md" }
    @{ From = "templates/backlog.md"; To = "docs/megaplan/backlog.md" }
    @{ From = "templates/glossary.md"; To = "docs/megaplan/glossary.md" }
    @{ From = "templates/backlog-item.md"; To = "docs/megaplan/backlog-items/_template.md" }
    @{ From = "templates/adr.md"; To = "docs/megaplan/adr/_template.md" }
    @{ From = "examples/simple-todo-api/"; To = "https://github.com/Gamebreack/megaplan/tree/main/examples/simple-todo-api/" }
    @{ From = "templates/wiki/"; To = "docs/megaplan/wiki/" }
)

# Pre-commit hook (bash script; requires Git Bash on Windows)
$HookScript = @'
#!/bin/bash
# Megaplan pre-commit hook — validates backlog integrity, glossary, and workflow gates
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT=""
DIR="$SCRIPT_DIR"
while [ "$DIR" != "/" ]; do
    if [ -f "$DIR/AGENTS.md" ] || [ -d "$DIR/.git" ]; then
        REPO_ROOT="$DIR"
        break
    fi
    DIR="$(dirname "$DIR")"
done

if [ -z "$REPO_ROOT" ]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

EXIT_CODE=0

if [ -f "$REPO_ROOT/docs/megaplan/backlog.md" ]; then
    echo "Megaplan: Validating backlog and active workflow gates..."
    ARGS=""
    if [ "$MEGAPLAN_RUN_VERIFIER" = "1" ]; then
        ARGS="--run-verifier"
    fi

    if ! python3 "$REPO_ROOT/scripts/megaplan/validate_backlog.py" "$REPO_ROOT" $ARGS 2>&1; then
        echo ""
        echo "Megaplan validation FAILED. Commit blocked."
        echo "Fix the errors above and try again."
        EXIT_CODE=1
    fi
fi

exit $EXIT_CODE
'@

# --------------------------------------------------------------------------- #
# Functions
# --------------------------------------------------------------------------- #

function Resolve-LatestVersion {
    param([string]$Ref = "")

    if ($Ref) {
        return $Ref
    }

    try {
        $release = Invoke-RestMethod -Uri $ApiUrl -ErrorAction Stop
        if ($release.tag_name) {
            return $release.tag_name
        }
        Write-Warning "GitHub Releases API returned no tag_name; falling back to main"
        return "main"
    } catch {
        Write-Warning "Could not reach GitHub Releases API ($($_.Exception.Message)); falling back to main"
        return "main"
    }
}

function Download-Framework {
    param([string]$Version, [string]$DestDir)

    $url = if ($Version -match "^v\d") {
        $TarballTagUrl -f $Version
    } else {
        $TarballBranchUrl -f $Version
    }

    $tempFile = Join-Path $DestDir "megaplan.tar.gz"
    Write-Host "Downloading $url ..."

    try {
        Invoke-WebRequest -Uri $url -OutFile $tempFile -ErrorAction Stop
    } catch {
        Write-Warning "Invoke-WebRequest failed ($($_.Exception.Message)); trying curl.exe..."
        & curl.exe -sSL -o $tempFile $url
        if ($LASTEXITCODE -ne 0) {
            throw "Download failed: curl.exe exited with code $LASTEXITCODE"
        }
    }

    Write-Host "Extracting archive ..."
    tar.exe -xzf $tempFile -C $DestDir
    if ($LASTEXITCODE -ne 0) {
        throw "tar.exe extraction failed with code $LASTEXITCODE"
    }

    # GitHub archives create a top-level dir like "megaplan-v2.0.0/"
    $extractedDir = Join-Path $DestDir "megaplan-$Version"
    if (-not (Test-Path $extractedDir)) {
        # Fallback: find the only subdirectory
        $dirs = Get-ChildItem -Directory -Path $DestDir -ErrorAction SilentlyContinue
        if ($dirs.Count -eq 0) {
            throw "No directory found after extraction in $DestDir"
        }
        $extractedDir = $dirs[0].FullName
    }

    return $extractedDir
}

function Install-Hook {
    param([string]$ProjectDir, [switch]$Force)

    $hookDir = Join-Path $ProjectDir ".git" "hooks"
    $hookPath = Join-Path $hookDir "pre-commit"

    if (-not (Test-Path $hookDir)) {
        Write-Warning ".git/hooks/ not found; skipping hook install"
        return $false
    }

    if ((Test-Path $hookPath) -and -not $Force) {
        Write-Host "Skipping pre-commit hook (exists; use -Force to overwrite)"
        return $false
    }

    # Write hook with Unix line endings for Git Bash
    [System.IO.File]::WriteAllText($hookPath, $HookScript)
    Write-Host "Pre-commit hook installed."
    return $true
}

function Invoke-SelfTest {
    param([string]$ProjectDir)

    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Warning "Python not found on PATH. Skipping self-test. Install Python 3.10+ to enable the self-test."
        return $false
    }

    $verifyScript = Join-Path $ProjectDir "scripts" "megaplan" "verify_workflow.py"
    if (-not (Test-Path $verifyScript)) {
        Write-Warning "Self-test script not found at $verifyScript"
        return $false
    }

    & python $verifyScript --selftest --project-dir $ProjectDir
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Self-test failed. Run 'python scripts/megaplan/verify_workflow.py --selftest' to investigate."
        return $false
    }

    Write-Host "Self-test: OK"
    return $true
}

function Write-NextSteps {
    param([string]$ProjectDir)

    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Edit $ProjectDir/docs/megaplan/megaplan.md to describe your project's vision."
    Write-Host "  2. Scope Cycle 0 in $ProjectDir/docs/megaplan/megaplan.md and create the first B-item."
    Write-Host "  3. Read $ProjectDir/docs/megaplan/methodology.md for the full workflow."
    Write-Host "  4. Re-run 'python scripts/megaplan/verify_workflow.py --selftest' any time to confirm the install is healthy."
}

function Apply-PathRewrites {
    param([string]$Content)

    $sortedRewrites = $PathRewrites | Sort-Object { $_.From.Length } -Descending
    foreach ($rewrite in $sortedRewrites) {
        if ($rewrite.To -like "$($rewrite.From)*") {
            # Negative lookahead prevents double-substitution (e.g., scripts/megaplan/ is not re-matched by scripts/)
            $pattern = [regex]::Escape($rewrite.From) + "(?!" + [regex]::Escape($rewrite.To.Substring($rewrite.From.Length)) + ")"
        } else {
            $pattern = [regex]::Escape($rewrite.From)
        }
        $Content = $Content -replace $pattern, $rewrite.To
    }
    return $Content
}

function Copy-LayoutFiles {
    param([string]$SrcDir, [string]$ProjectDir, [switch]$IncludeWiki, [switch]$ForceOverwrite)

    # Merge layout with optional wiki entries
    $allLayout = @{}
    $Layout.GetEnumerator() | ForEach-Object { $allLayout[$_.Key] = $_.Value }
    if ($IncludeWiki) {
        $WikiLayout.GetEnumerator() | ForEach-Object { $allLayout[$_.Key] = $_.Value }
    }

    $written = 0
    $skipped = 0

    $sortedEntries = $allLayout.GetEnumerator() | Sort-Object { $_.Key.Length } -Descending
    foreach ($entry in $sortedEntries) {
        $src = Join-Path $SrcDir $entry.Key
        $dst = Join-Path $ProjectDir $entry.Value

        if (-not (Test-Path $src)) {
            Write-Warning "Source not found: $src"
            continue
        }

        if (Test-Path $dst) {
            if (-not $ForceOverwrite) {
                Write-Host "Skipping $($entry.Value) (exists; use -Force to overwrite)"
                $skipped++
                continue
            }
        }

        # Ensure parent directory exists
        $parentDir = Split-Path $dst -Parent
        if (-not (Test-Path $parentDir)) {
            New-Item -ItemType Directory -Force -Path $parentDir | Out-Null
        }

        $content = Get-Content $src -Raw
        if ($content) {
            $content = Apply-PathRewrites -Content $content
            Set-Content -Path $dst -Value $content -NoNewline -Encoding UTF8
        } else {
            # Empty file; just ensure it exists
            New-Item -ItemType File -Force -Path $dst | Out-Null
        }
        $written++
    }

    # Copy scripts to scripts/megaplan/ (no path rewriting for scripts)
    $scriptsDir = Join-Path $ProjectDir "scripts" "megaplan"
    if (-not (Test-Path $scriptsDir)) {
        New-Item -ItemType Directory -Force -Path $scriptsDir | Out-Null
    }
    foreach ($script in $Scripts) {
        $src = Join-Path $SrcDir "scripts" $script
        $dst = Join-Path $scriptsDir $script
        if (-not (Test-Path $src)) {
            Write-Warning "Script source not found: $src"
            continue
        }
        if ((Test-Path $dst) -and -not $ForceOverwrite) {
            $skipped++
            continue
        }
        Copy-Item $src $dst -Force
    }

    Write-Host "Lay-out: $written files written, $skipped skipped."
}

function Main {
    $resolvedDir = [System.IO.Path]::GetFullPath($ProjectDir)

    # 1. Resolve version
    $version = Resolve-LatestVersion -Ref $Ref
    Write-Host "Megaplan bootstrap: version $version"

    # 2. Get framework source
    if ($FromLocal) {
        $srcDir = [System.IO.Path]::GetFullPath($FromLocal)
        if (-not (Test-Path $srcDir)) {
            Write-Error "--from-local path is not a directory: $srcDir"
            return 1
        }
    } else {
        $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) "megaplan_$(Get-Random)"
        New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
        try {
            $srcDir = Download-Framework -Version $version -DestDir $tempDir
        } catch {
            Write-Error "Download failed: $_"
            if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue }
            return 1
        }
    }

    # 3. Lay out files
    Copy-LayoutFiles -SrcDir $srcDir -ProjectDir $resolvedDir -IncludeWiki:$WithWiki -ForceOverwrite:$Force

    # 4. Install pre-commit hook
    if (-not $SkipHook) {
        Install-Hook -ProjectDir $resolvedDir -Force:$Force
    }

    # 5. Self-test
    if (-not $SkipSelfTest) {
        Invoke-SelfTest -ProjectDir $resolvedDir
    }

    # 6. Next steps
    Write-NextSteps -ProjectDir $resolvedDir

    return 0
}

# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

exit Main

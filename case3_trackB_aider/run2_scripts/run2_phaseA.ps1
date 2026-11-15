# Phase A (unattended): clean baseline -> baseline tests -> Aider audit with the assignment's own prompt.
# ASCII only on purpose (Windows PowerShell 5.1 safe).
$ErrorActionPreference = 'Continue'
$env:PYTHONUTF8 = '1'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$cs3    = Split-Path -Parent $MyInvocation.MyCommand.Path
$orig   = Join-Path $cs3 'SOEN-6431-Group-Project'
$run    = Join-Path $cs3 'run2'
$ev     = Join-Path $cs3 'run2_evidence'
$aider  = Join-Path $orig '.venv\Scripts\aider.exe'
$py0    = Join-Path $orig '.venv\Scripts\python.exe'
$prompt = Join-Path $cs3 'run2_prompts\audit.txt'
$sha    = '5b604c37c6c67e18e7c3e9aee6c88a8c22b98345'
$remote = 'https://github.com/ABCWarrior/SOEN-6431-Group-Project.git'

New-Item -ItemType Directory -Force -Path $ev | Out-Null
$log = Join-Path $ev 'phaseA_log.txt'
function Say([string]$m) {
    $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $m
    Write-Host $line
    Add-Content -Path $log -Value $line
}

Say 'Phase A started. Keep the laptop plugged in and awake (do not close the lid). You can go study.'

if (-not $env:GEMINI_API_KEY) { Say 'STOP: GEMINI_API_KEY is not set in this PowerShell window. Set it and run again.'; exit 1 }
if (-not (Test-Path $aider))  { Say "STOP: aider.exe not found: $aider"; exit 1 }
if (-not (Test-Path $prompt)) { Say "STOP: prompt file missing: $prompt"; exit 1 }

# 1) Clean clone at the pristine baseline commit (no teammate changes, no case3_trackB folder)
if (-not (Test-Path (Join-Path $run '.git'))) {
    Say 'Cloning a clean copy at the baseline commit...'
    git clone --quiet "$orig" "$run" 2>&1 | Out-Null
    git -C "$run" checkout -q -b case3-groupB-aider-v2 $sha 2>&1 | Out-Null
    git -C "$run" remote set-url origin $remote
    Add-Content -Path (Join-Path $run '.git\info\exclude') -Value @('.venv-test/', '.aider*', '__pycache__/', '*.pyc')
}
$head = (git -C "$run" rev-parse HEAD).Trim()
if ($head -ne $sha) { Say "STOP: clone is at $head, expected $sha"; exit 1 }
Say "Baseline OK: $head"

# 2) Test environment (fresh venv) + baseline test run BEFORE any AI edit
$pyt = Join-Path $run '.venv-test\Scripts\python.exe'
if (-not (Test-Path $pyt)) {
    Say 'Creating test venv and installing HTTPie + test dependencies (a few minutes)...'
    & $py0 -m venv (Join-Path $run '.venv-test')
    Push-Location $run
    & $pyt -m pip install -q --disable-pip-version-check -e . pytest pytest-httpbin responses pytest-mock 2>&1 | Out-File (Join-Path $ev 'pip_install.txt') -Encoding utf8
    Pop-Location
}
$bt = Join-Path $ev 'tests_baseline.txt'
if (-not (Test-Path $bt)) {
    Say 'Running the baseline test suite on clean code (a few minutes)...'
    Push-Location $run
    & $pyt -m pytest tests -q --tb=no -rfE -p no:cacheprovider 2>&1 | Out-File $bt -Encoding utf8
    Pop-Location
    $sum = (Select-String -Path $bt -Pattern ' passed' | Select-Object -Last 1)
    if ($sum) { Say ('Baseline tests: ' + $sum.Line) } else { Say 'Baseline tests: could not read summary (see tests_baseline.txt)' }
}

# 3) Aider audit: the assignment's own audit prompt, verbatim, over the whole httpie/ package
Push-Location $run
$all = @(Get-ChildItem -Path 'httpie' -Recurse -Filter '*.py' | ForEach-Object { $_.FullName.Substring($run.Length + 1) } | Sort-Object)
$g1  = @($all | Where-Object { ($_ -match '^httpie\\cli\\') -or ($_ -match '^httpie\\[^\\]+\.py$') })
$g2  = @($all | Where-Object { $_ -match '^httpie\\output\\' })
$g3  = @($all | Where-Object { ($g1 -notcontains $_) -and ($g2 -notcontains $_) })
Say ("Files: all={0} g1={1} g2={2} g3={3}" -f $all.Count, $g1.Count, $g2.Count, $g3.Count)

function Try-Audit([string[]]$files, [string]$tag) {
    $models = @('gemini/gemini-3.8-flash', 'gemini/gemini-3.8-flash', 'gemini/gemini-3.8-flash', 'gemini/gemini-3.7-flash', 'gemini/gemini-2.5-pro')
    $n = 0
    foreach ($m in $models) {
        $n++
        $out = Join-Path $ev ('audit_{0}_try{1}.txt' -f $tag, $n)
        Say ('Audit [{0}] try {1}/{2} with {3} ({4} files)...' -f $tag, $n, $models.Count, $m, $files.Count)
        $aargs = @('--model', $m, '--chat-mode', 'ask', '--yes-always', '--no-gitignore', '--no-check-update', '--no-show-model-warnings', '--no-pretty', '--no-stream', '--timeout', '600', '--message-file', $prompt) + $files
        & $aider @aargs 2>&1 | Out-File $out -Encoding utf8
        if (Select-String -Path $out -Pattern 'Tokens: .* received' -Quiet) {
            Say ('Audit [{0}] answered OK with {1}.' -f $tag, $m)
            return $m
        }
        Say ('Audit [{0}] did not finish (provider error/timeout). Waiting 90 s, then retrying...' -f $tag)
        Start-Sleep -Seconds 90
    }
    return $null
}

$status = 'FAILED'
$used = @()
$m = Try-Audit $all 'whole'
if ($m) {
    $status = 'WHOLE_OK'; $used += ('whole:' + $m)
} else {
    Say 'Whole-package audit failed. Falling back to 3 chunks, SAME prompt.'
    $okAll = $true
    $chunks = @(@('g1', $g1), @('g2', $g2), @('g3', $g3))
    foreach ($c in $chunks) {
        $mm = Try-Audit $c[1] $c[0]
        if ($mm) { $used += ($c[0] + ':' + $mm) } else { $okAll = $false }
    }
    if ($okAll) { $status = 'CHUNKED_OK' } else { $status = 'PARTIAL_OR_FAILED' }
}
Pop-Location

Copy-Item (Join-Path $run '.aider.chat.history.md') (Join-Path $ev 'aider.chat.history.md') -Force -ErrorAction SilentlyContinue
$ver = (& $aider --version 2>&1 | Out-String).Trim()
@("date: $(Get-Date -Format s)", "base: $sha", "aider: $ver", "status: $status", "runs: $($used -join '; ')") | Set-Content (Join-Path $ev 'meta.txt')

Say "PHASE A FINISHED. status = $status"
Say 'Go back to the Claude chat and type:  A done'

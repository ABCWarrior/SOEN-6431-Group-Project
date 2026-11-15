# Phase A, version 2 (unattended). Smaller requests, quota-aware, no browser pop-ups.
# Scope = the assignment's own target row for HTTPie: httpie/cli (argument parsing) + httpie/core.py (execution).
# Prompt = the assignment's own audit prompt, verbatim. ASCII only on purpose.
$ErrorActionPreference = 'Continue'
$env:PYTHONUTF8 = '1'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

$cs3    = Split-Path -Parent $MyInvocation.MyCommand.Path
$orig   = Join-Path $cs3 'SOEN-6431-Group-Project'
$run    = Join-Path $cs3 'run2'
$ev     = Join-Path $cs3 'run2_evidence'
$aider  = Join-Path $orig '.venv\Scripts\aider.exe'
$py0    = Join-Path $orig '.venv\Scripts\python.exe'
$prompt = Join-Path $cs3 'run2_prompts\audit.txt'
$sha    = '5b604c37c6c67e18e7c3e9aee6c88a8c22b98345'
$remote = 'https://github.com/ABCWarrior/SOEN-6431-Group-Project.git'

# Stop Aider from opening browser tabs on every provider error (points Python's webbrowser at a no-op).
$env:BROWSER = Join-Path $cs3 'run2_noop.cmd'

New-Item -ItemType Directory -Force -Path $ev | Out-Null
$log = Join-Path $ev 'phaseA2_log.txt'
function Say([string]$m) {
    $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $m
    Write-Host $line
    Add-Content -Path $log -Value $line
}
Say 'Phase A v2 started. Keep the laptop plugged in and awake. You can go study.'

if (-not $env:GEMINI_API_KEY) { Say 'STOP: GEMINI_API_KEY is not set in this PowerShell window. Set it and run again.'; exit 1 }
if (-not (Test-Path $aider))  { Say "STOP: aider.exe not found: $aider"; exit 1 }
if (-not (Test-Path $prompt)) { Say "STOP: prompt file missing: $prompt"; exit 1 }

# 1) Clean clone at the pristine baseline (skipped if it already exists)
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

# 2) Test environment + baseline tests (skipped if already done)
$pyt = Join-Path $run '.venv-test\Scripts\python.exe'
if (-not (Test-Path $pyt)) {
    Say 'Creating test venv (a few minutes)...'
    & $py0 -m venv (Join-Path $run '.venv-test')
    Push-Location $run
    & $pyt -m pip install -q --disable-pip-version-check -e . pytest pytest-httpbin responses pytest-mock 2>&1 | Out-File (Join-Path $ev 'pip_install.txt') -Encoding utf8
    Pop-Location
}
$bt = Join-Path $ev 'tests_baseline.txt'
if (-not (Test-Path $bt)) {
    Say 'Running the baseline test suite (a few minutes)...'
    Push-Location $run
    & $pyt -m pytest tests -q --tb=no -rfE -p no:cacheprovider 2>&1 | Out-File $bt -Encoding utf8
    Pop-Location
}
$sum = (Select-String -Path $bt -Pattern ' passed' | Select-Object -Last 1)
if ($sum) { Say ('Baseline tests: ' + $sum.Line) }

# 3) Scope: httpie/cli/** + httpie/core.py, split into batches of at most 45,000 characters (about 13k tokens each)
Push-Location $run
$scope = @(Get-ChildItem -Path 'httpie\cli' -Recurse -Filter '*.py' | Sort-Object FullName | ForEach-Object { $_.FullName.Substring($run.Length + 1) })
$scope += 'httpie\core.py'
$batches = @()
$cur = @(); $curSize = 0
foreach ($f in $scope) {
    $sz = (Get-Item (Join-Path $run $f)).Length
    if (($cur.Count -gt 0) -and (($curSize + $sz) -gt 45000)) { $batches += ,$cur; $cur = @(); $curSize = 0 }
    $cur += $f; $curSize += $sz
}
if ($cur.Count -gt 0) { $batches += ,$cur }
Say ('Scope: {0} files in {1} batches' -f $scope.Count, $batches.Count)

# 4) Quota-aware model picker: a tiny 1-request probe before every expensive Aider run.
#    (One failed Aider run can burn ~9 requests of the 20/day free quota; a probe burns 1.)
$models = @('gemini/gemini-3.8-flash', 'gemini/gemini-3.7-flash', 'gemini/gemini-3.6-flash', 'gemini/gemini-2.5-flash')
$dead = @{}
$script:probeBudget = 10

function Probe-Model([string]$m) {
    $name = $m -replace '^gemini/', ''
    $uri  = "https://generativelanguage.googleapis.com/v1beta/models/${name}:generateContent"
    $body = '{"contents":[{"parts":[{"text":"Reply with the single word OK."}]}],"generationConfig":{"maxOutputTokens":16}}'
    try {
        Invoke-RestMethod -Method Post -Uri $uri -Headers @{ 'x-goog-api-key' = $env:GEMINI_API_KEY } -ContentType 'application/json' -Body $body -TimeoutSec 90 | Out-Null
        return 'OK'
    } catch {
        $txt = ''
        try { $txt = [string]$_.ErrorDetails.Message } catch {}
        if (-not $txt) { $txt = [string]$_.Exception.Message }
        if ($txt -match 'PerDay') { return 'DAY' }
        if ($txt -match 'PerMinute|RESOURCE_EXHAUSTED|429') { return 'MIN' }
        if ($txt -match 'UNAVAILABLE|503|overloaded|high demand') { return 'BUSY' }
        return 'ERR'
    }
}

function Get-LiveModel {
    while ($script:probeBudget -gt 0) {
        $waiting = $false
        foreach ($m in $models) {
            if ($dead.ContainsKey($m)) { continue }
            if ($script:probeBudget -le 0) { break }
            $script:probeBudget = $script:probeBudget - 1
            $r = Probe-Model $m
            Say ('Probe {0}: {1} (probes left: {2})' -f $m, $r, $script:probeBudget)
            if ($r -eq 'OK') { return $m }
            if ($r -eq 'DAY') { $dead[$m] = $true } else { $waiting = $true }
        }
        if ($dead.Count -ge $models.Count) { return $null }
        if ($waiting) { Say 'Servers busy or per-minute limit. Waiting 75 s...'; Start-Sleep -Seconds 75 }
    }
    return $null
}

# 5) Audit each batch with the assignment's own prompt (verbatim). Same model for main AND weak model.
$done = @(); $failed = @()
$bi = 0
foreach ($b in $batches) {
    $bi++
    $ok = $false
    for ($try = 1; ($try -le 2) -and (-not $ok); $try++) {
        $m = Get-LiveModel
        if (-not $m) { break }
        $out = Join-Path $ev ('audit_b{0}_try{1}.txt' -f $bi, $try)
        Say ('Audit batch {0}/{1} ({2} files) with {3}, try {4}...' -f $bi, $batches.Count, $b.Count, $m, $try)
        $aargs = @('--model', $m, '--weak-model', $m, '--chat-mode', 'ask', '--yes-always', '--no-gitignore', '--no-check-update', '--no-show-model-warnings', '--no-pretty', '--no-stream', '--timeout', '300', '--message-file', $prompt) + $b
        & $aider @aargs 2>&1 | Out-File $out -Encoding utf8
        if (Select-String -Path $out -Pattern 'Tokens: .* received' -Quiet) {
            $ok = $true
            $done += ('b{0}:{1}' -f $bi, $m)
            Say ('Batch {0} answered OK with {1}.' -f $bi, $m)
        } else {
            Say ('Batch {0} did not finish.' -f $bi)
        }
    }
    if (-not $ok) { $failed += $bi }
    if ($bi -lt $batches.Count) { Start-Sleep -Seconds 20 }
}
Pop-Location

if ($failed.Count -eq 0) { $status = 'ALL_BATCHES_OK' }
elseif ($done.Count -gt 0) { $status = 'PARTIAL (failed batches: ' + ($failed -join ',') + ')' }
else { $status = 'NOTHING_FINISHED (daily quota or servers; try again after 03:15 Toronto time)' }

Copy-Item (Join-Path $run '.aider.chat.history.md') (Join-Path $ev 'aider.chat.history.md') -Force -ErrorAction SilentlyContinue
$ver = (& $aider --version 2>&1 | Out-String).Trim()
@("date: $(Get-Date -Format s)", "base: $sha", "aider: $ver", "scope: httpie/cli/** + httpie/core.py", "status: $status", "runs: $($done -join '; ')") | Set-Content (Join-Path $ev 'meta2.txt')

Say "PHASE A v2 FINISHED. status = $status"
Say 'Go back to the Claude chat and type:  A done'

# Phase B (unattended): Aider refactors ITS OWN candidate pair #1 using the assignment's refactoring prompt
# (only [File A]/[File B] filled in mechanically), then full tests vs baseline, then push. ASCII only.
$ErrorActionPreference = 'Continue'
$env:PYTHONUTF8 = '1'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

$cs3    = Split-Path -Parent $MyInvocation.MyCommand.Path
$orig   = Join-Path $cs3 'SOEN-6431-Group-Project'
$run    = Join-Path $cs3 'run2'
$ev     = Join-Path $cs3 'run2_evidence'
$aider  = Join-Path $orig '.venv\Scripts\aider.exe'
$pyt    = Join-Path $run '.venv-test\Scripts\python.exe'
$prompt = Join-Path $cs3 'run2_prompts\refactor.txt'
$sha    = '5b604c37c6c67e18e7c3e9aee6c88a8c22b98345'
$target = 'httpie\cli\nested_json\parse.py'
$env:BROWSER = Join-Path $cs3 'run2_noop.cmd'

New-Item -ItemType Directory -Force -Path $ev | Out-Null
$log = Join-Path $ev 'phaseB_log.txt'
function Say([string]$m) {
    $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $m
    Write-Host $line
    try { Add-Content -Path $log -Value $line -ErrorAction Stop } catch { }
}
Say 'Phase B started. Keep the laptop plugged in and awake. You can go study.'

if (-not $env:GEMINI_API_KEY) { Say 'STOP: GEMINI_API_KEY is not set in this PowerShell window.'; exit 1 }
foreach ($p in @($aider, $pyt, $prompt, (Join-Path $run $target))) { if (-not (Test-Path $p)) { Say "STOP: missing $p"; exit 1 } }

# quota-aware model picker (same as phase A v2)
$models = @('gemini/gemini-3.8-flash', 'gemini/gemini-3.7-flash', 'gemini/gemini-3.6-flash', 'gemini/gemini-2.5-flash')
$dead = @{}
$script:probeBudget = 8
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

Push-Location $run
# housekeeping: a stale empty .git\index.lock (left by an earlier read-only git probe) blocked Aider's commit on the first attempt
if (Test-Path '.git\index.lock') { Remove-Item '.git\index.lock' -Force -ErrorAction SilentlyContinue; Say 'Removed stale .git/index.lock' }
# archive the earlier attempts (Aider edited the file but could not commit) and restore the baseline file
foreach ($n in 1,2) { $f = Join-Path $ev ('refactor_try{0}.txt' -f $n); if (Test-Path $f) { Move-Item $f (Join-Path $ev ('refactor_try{0}_earlier_lockfail.txt' -f $n)) -Force } }
git checkout -- $target 2>$null
Say 'Restored baseline parse.py before the run.'
$before = (git rev-parse HEAD).Trim()
Say "Branch tip before the AI edit: $before"

# 1) The refactoring step: assignment prompt, Aider in code mode, file = Aider's own pair #1
$edited = $false
$usedModel = ''
for ($try = 1; ($try -le 2) -and (-not $edited); $try++) {
    $m = Get-LiveModel
    if (-not $m) { break }
    $out = Join-Path $ev ('refactor_try{0}.txt' -f $try)
    Say ('Refactor try {0} with {1}...' -f $try, $m)
    $aargs = @('--model', $m, '--weak-model', $m, '--yes-always', '--no-gitignore', '--no-check-update', '--no-show-model-warnings', '--no-pretty', '--no-stream', '--timeout', '300', '--message-file', $prompt, $target)
    & $aider @aargs 2>&1 | Out-File $out -Encoding utf8
    $now = (git rev-parse HEAD).Trim()
    if ($now -ne $before) { $edited = $true; $usedModel = $m; Say "Aider committed its own edit: $now" }
    else { Say 'No commit from Aider on this try.' }
}

if (-not $edited) {
    Pop-Location
    Say 'PHASE B FINISHED. status = NO_EDIT (provider busy / quota / Aider made no change). Tell Claude: B done'
    exit 0
}

# 2) Evidence of what the agent changed
git log --format='%H %an %s' "$before..HEAD" | Out-File (Join-Path $ev 'refactor_commits.txt') -Encoding utf8
git diff "$before" HEAD | Out-File (Join-Path $ev 'refactor.diff') -Encoding utf8
git diff --stat "$before" HEAD | Out-File (Join-Path $ev 'refactor_stat.txt') -Encoding utf8
Copy-Item (Join-Path $run '.aider.chat.history.md') (Join-Path $ev 'aider.chat.history.after_B.md') -Force -ErrorAction SilentlyContinue

# 3) Tests: the nested-JSON tests first (fast), then the full suite, compared with the clean baseline
Say 'Running tests/test_json.py...'
& $pyt -m pytest tests/test_json.py -q --tb=short -p no:cacheprovider 2>&1 | Out-File (Join-Path $ev 'tests_after_json.txt') -Encoding utf8
Say ((Select-String -Path (Join-Path $ev 'tests_after_json.txt') -Pattern ' passed| failed' | Select-Object -Last 1).Line)
Say 'Running the full test suite (about 4 minutes)...'
$ta = Join-Path $ev 'tests_after.txt'
& $pyt -m pytest tests -q --tb=no -rfE -p no:cacheprovider 2>&1 | Out-File $ta -Encoding utf8
$bt = Join-Path $ev 'tests_baseline.txt'
function Get-Failed([string]$f) { @(Select-String -Path $f -Pattern '^(FAILED|ERROR) ' | ForEach-Object { ($_.Line -split ' - ')[0] }) }
$bf = Get-Failed $bt
$af = Get-Failed $ta
$new = @($af | Where-Object { $bf -notcontains $_ })
Say ('Baseline: ' + (Select-String -Path $bt -Pattern ' passed' | Select-Object -Last 1).Line)
Say ('After   : ' + (Select-String -Path $ta -Pattern ' passed' | Select-Object -Last 1).Line)
Say ('NEW FAILURES vs clean baseline: ' + $new.Count)
$new | Out-File (Join-Path $ev 'tests_new_failures.txt') -Encoding utf8

# 4) Push the branch (+ the baseline commit as a base branch so the PR shows only the AI diff)
Say 'Pushing branches...'
git push -u origin case3-groupB-aider-v2 2>&1 | Out-File (Join-Path $ev 'push_log.txt') -Encoding utf8
git push origin "${sha}:refs/heads/case3-groupB-base" 2>&1 | Out-File (Join-Path $ev 'push_base_log.txt') -Encoding utf8
Pop-Location

@("date: $(Get-Date -Format s)", "model: $usedModel", "target: $target", "new_failures: $($new.Count)") | Set-Content (Join-Path $ev 'metaB.txt')
Say 'PHASE B FINISHED.'
Say 'Open this link and click "Create pull request" (title: Refactor can_advance() duplication in nested_json/parse.py):'
Say 'https://github.com/ABCWarrior/SOEN-6431-Group-Project/compare/case3-groupB-base...case3-groupB-aider-v2?expand=1'
Say 'Then go back to the Claude chat and type:  B done'

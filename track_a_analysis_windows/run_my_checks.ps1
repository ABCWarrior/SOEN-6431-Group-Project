# run_my_checks.ps1  (v3, logs + methodology)
# A Windows version of the Track A checks for HTTPie. No Docker, no npm, no WSL.
#
# What it does:
#   1. Creates one Python virtual environment (first run only) and installs 5 tools into it.
#   2. Runs the checks on the HTTPie repo.
#   3. Saves every tool's FULL output into the raw folder, each file starting with a header
#      (exact command, date, platform, repo commit), so every log is self-describing evidence.
#   4. Saves code snippets (with line numbers) that the report talks about: 8_snippets.txt
#   5. Prints a table of "expected (from the Track A report)" against "what you got".
#
# Run it from PowerShell, from this folder (track_a_analysis_windows, inside the repo):
#   powershell -ExecutionPolicy Bypass -File .\run_my_checks.ps1
#
# To undo everything: delete the raw folder and the venv folder (default: $HOME\tda-venv).
# Nothing is installed globally, and the repo is only read, never changed.

param(
  [string]$Repo = (Split-Path $PSScriptRoot -Parent),
  [string]$Venv = (Join-Path $HOME "tda-venv"),
  [string]$Python = "",   # optional: full path to python.exe if the script cannot find it
  [string]$Python312 = "",  # optional: full path to a Python 3.12 python.exe (used only for the pytest step)
  [string]$TestVenv = (Join-Path $HOME "tda-test-venv")
)

# Try a few places for a working Python 3, and return the first one that answers "Python 3.x".
function Find-Python([string]$Wanted) {
  $candidates = @()
  if ($Wanted) { $candidates += $Wanted }
  $candidates += "python", "py"
  foreach ($v in "312", "311", "313", "310") {
    $candidates += (Join-Path $env:LOCALAPPDATA "Programs\Python\Python$v\python.exe")
  }
  $saved = $ErrorActionPreference
  $ErrorActionPreference = "SilentlyContinue"
  foreach ($c in $candidates) {
    if ($c -match "[\\/]" -and -not (Test-Path $c)) { continue }
    $answer = "$(& $c --version 2>&1)"
    if ($answer -match "^Python 3\.\d+") { $ErrorActionPreference = $saved; return $c }
  }
  $ErrorActionPreference = $saved
  return $null
}

$ErrorActionPreference = "Continue"
$out = Join-Path $PSScriptRoot "raw"

if (-not (Test-Path (Join-Path $Repo "httpie"))) {
  Write-Host "Cannot find the httpie folder inside: $Repo" -ForegroundColor Red
  Write-Host "Pass the repo path with -Repo, for example: -Repo 'D:\path\to\SOEN-6431-Group-Project'"
  exit 1
}
New-Item -ItemType Directory -Force -Path $out | Out-Null

# ---- 0. environment (first run only) ----------------------------------------
$py = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Host "[0] Creating a virtual environment at $Venv (first run only)..." -ForegroundColor Cyan
  $found = Find-Python $Python
  if (-not $found) {
    Write-Host "Could not find a working Python 3." -ForegroundColor Red
    Write-Host "If you know where python.exe is, run again with: -Python 'C:\full\path\to\python.exe'"
    exit 1
  }
  Write-Host "    using Python: $found"
  & $found -m venv $Venv
  if (-not (Test-Path $py)) {
    Write-Host "Python was found but the venv could not be created." -ForegroundColor Red
    exit 1
  }
  & $py -m pip install -q lizard==1.25.0 radon==6.0.1 flake8==7.5.0 pylint==4.1.3 vulture==2.16
}
$bin = Join-Path $Venv "Scripts"
Set-Location $Repo

$commit = "$(git rev-parse --short HEAD 2>&1)"
$pyver  = "$(& $py --version 2>&1)"
$stamp  = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Count-Lines($text) { return (@($text | Where-Object { $_ -and $_.ToString().Trim() -ne "" })).Count }

# Write a log file that starts with a header saying exactly how it was produced.
function Save-Log([string]$path, [string]$cmd, $lines) {
  $hdr = @(
    "# command  : $cmd",
    "# run at   : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "# platform : Windows, PowerShell $($PSVersionTable.PSVersion), $pyver",
    "# commit   : $commit (repo: $Repo)",
    "# ------------------------------------------------------------"
  )
  $body = @($lines) | ForEach-Object { "$_" }
  ($hdr + $body) | Out-File -Encoding utf8 $path
}

function Tool-Version([string]$exe) {
  $v = & "$bin\$exe" --version 2>&1 | Select-Object -First 1
  return "$v"
}

$rows = @()

# ---- 1. Lizard: complexity per function ----------------------------------------
Write-Host "[1] Lizard: complexity per function" -ForegroundColor Cyan
$full = & "$bin\lizard.exe" httpie 2>&1
Save-Log "$out\1_lizard_full.txt" "lizard httpie" $full
$csv = & "$bin\lizard.exe" httpie --csv 2>&1
Save-Log "$out\1_lizard_functions_csv.txt" "lizard httpie --csv" $csv
$warn = & "$bin\lizard.exe" httpie -w 2>&1
Save-Log "$out\1_lizard_over15.txt" "lizard httpie -w  (default threshold: CCN > 15)" $warn
$n = Count-Lines ($warn | Where-Object { "$_" -match "warning:" })
$rows += [pscustomobject]@{ Check = "Lizard: functions with complexity above 15"; Expected = "4"; YouGot = $n }
$full | Select-Object -Last 6 | ForEach-Object { Write-Host "    $_" }
$lz2 = & "$bin\lizard.exe" httpie -x "*\tests\*" 2>&1
Save-Log "$out\1_lizard_spec_command.txt" 'lizard httpie -x "**/tests/*"   (command as written in the spec, section 5)' $lz2

# ---- 2. Radon: grades and maintainability --------------------------------------
Write-Host "[2] Radon: complexity grades and maintainability" -ForegroundColor Cyan
$cc = & "$bin\radon.exe" cc httpie -s -nc 2>&1
Save-Log "$out\2_radon_cc.txt" "radon cc httpie -s -nc  (only blocks graded C or worse)" $cc
$n = Count-Lines ($cc | Where-Object { "$_" -match " - [C-F]( |$)" })
$rows += [pscustomobject]@{ Check = "Radon: blocks graded C or worse"; Expected = "about 14"; YouGot = $n }

$mi = & "$bin\radon.exe" mi httpie -s 2>&1
Save-Log "$out\2_radon_mi.txt" "radon mi httpie -s  (maintainability index per file)" $mi
$lowest = $mi | Where-Object { "$_" -match "\(\d" } |
  Sort-Object { [double](("$_" -replace '.*\(([\d.]+)\).*', '$1')) } | Select-Object -First 1
$rows += [pscustomobject]@{ Check = "Radon: least maintainable file"; Expected = "argparser.py, about 24.7"; YouGot = ("$lowest" -replace '\s+', ' ') }

# ---- 3. Flake8: too-complex functions ------------------------------------------
Write-Host "[3] Flake8: functions that are too complex" -ForegroundColor Cyan
$fl = & "$bin\flake8.exe" httpie --max-complexity=10 --select=C901 2>&1
Save-Log "$out\3_flake8_C901.txt" "flake8 httpie --max-complexity=10 --select=C901" $fl
$n = Count-Lines ($fl | Where-Object { "$_" -match "C901" })
$rows += [pscustomobject]@{ Check = "Flake8: C901 (too complex) warnings"; Expected = "about 9"; YouGot = $n }
$flf = & "$bin\flake8.exe" httpie --max-complexity=10 --select=E,F,W,C90 2>&1
Save-Log "$out\3_flake8_full.txt" "flake8 httpie --max-complexity=10 --select=E,F,W,C90   (the spec command, limited to the core rule families so installed plugins do not add findings)" $flf
$byfile = $flf | Where-Object { "$_" -match "^[^:]+:\d+:\d+:" } |
  ForEach-Object { ("$_" -split ":")[0] } | Group-Object | Sort-Object Count -Descending |
  ForEach-Object { "{0,5}  {1}" -f $_.Count, $_.Name }
Save-Log "$out\3_flake8_violations_by_file.txt" "flake8 httpie --max-complexity=10, counted per file (rule violation counts)" $byfile
$nflake = Count-Lines ($flf | Where-Object { "$_" -match "^[^:]+:\d+:\d+:" })
$rows += [pscustomobject]@{ Check = "Flake8: all violations (default rules)"; Expected = "9"; YouGot = $nflake }

# Same command as the original run_track_a.sh: with the bugbear and cognitive-complexity plugins
& $py -m pip install -q flake8-bugbear flake8-cognitive-complexity
$flp = & "$bin\flake8.exe" httpie --max-complexity=10 --max-cognitive-complexity=15 --select=C90,CCR,B,E,W,F --ignore=E501,W503 --statistics --count 2>&1
Save-Log "$out\3_flake8_plugins.txt" "flake8 httpie --max-complexity=10 --max-cognitive-complexity=15 --select=C90,CCR,B,E,W,F --ignore=E501,W503 --statistics --count  (as in run_track_a.sh, plugins: bugbear, cognitive-complexity)" $flp
$flpLines = $flp | Where-Object { "$_" -match "^[^:]+:\d+:\d+:" }
$rows += [pscustomobject]@{ Check = "Flake8 + plugins: C901 and CCR001 (complexity)"; Expected = "22"; YouGot = (Count-Lines ($flpLines | Where-Object { "$_" -match "C901|CCR001" })) }
$rows += [pscustomobject]@{ Check = "Flake8 + plugins: all findings"; Expected = "39"; YouGot = (Count-Lines $flpLines) }

# ---- 4. Vulture: code nobody calls ---------------------------------------------
Write-Host "[4] Vulture: possibly unused code" -ForegroundColor Cyan
$vu = & "$bin\vulture.exe" httpie --min-confidence 60 2>&1
Save-Log "$out\4_vulture.txt" "vulture httpie --min-confidence 60" $vu
$n = Count-Lines $vu
$rows += [pscustomobject]@{ Check = "Vulture: unused-code candidates"; Expected = "about 35"; YouGot = $n }

# ---- 5. Pylint: import cycles (takes a little while) ---------------------------
Write-Host "[5] Pylint: import cycles (this one takes a minute)" -ForegroundColor Cyan
$pl = & "$bin\pylint.exe" httpie --disable=all --enable=cyclic-import 2>&1
Save-Log "$out\5_pylint_cycles.txt" "pylint httpie --disable=all --enable=cyclic-import" $pl
$n = Count-Lines ($pl | Where-Object { "$_" -match "R0401" })
$rows += [pscustomobject]@{ Check = "Pylint: import-cycle paths"; Expected = "5"; YouGot = $n }

# ---- 6. git: how often core.py changed -----------------------------------------
Write-Host "[6] git: how often httpie/core.py changed since 2019" -ForegroundColor Cyan
$g = git log --oneline --no-merges --since=2019-01-01 -- httpie/core.py 2>&1
Save-Log "$out\6_git_core_changes.txt" "git log --oneline --no-merges --since=2019-01-01 -- httpie/core.py" $g
$n = Count-Lines $g
$rows += [pscustomobject]@{ Check = "git: commits touching core.py since 2019"; Expected = "37"; YouGot = $n }

# ---- 7. Pylint design checks (extra log, no expected number) -------------------
Write-Host "[7] Pylint: too many branches / statements / arguments" -ForegroundColor Cyan
$pd = & "$bin\pylint.exe" httpie --disable=all --enable=too-many-branches,too-many-statements,too-many-arguments,too-many-locals 2>&1
Save-Log "$out\7_pylint_design.txt" "pylint httpie --disable=all --enable=too-many-branches,too-many-statements,too-many-arguments,too-many-locals" $pd

# ---- 7b. Churn per file (hotspot ingredient: change frequency) -----------------
Write-Host "[7b] git: most-changed files since 2019" -ForegroundColor Cyan
$ch = git log --since=2019-01-01 --no-merges --name-only --pretty=format: -- httpie 2>&1 |
  Where-Object { $_ -and "$_".Trim() } | Group-Object | Sort-Object Count -Descending |
  Select-Object -First 25 | ForEach-Object { "{0,5}  {1}" -f $_.Count, $_.Name }
Save-Log "$out\7b_git_churn_by_file.txt" "git log --since=2019-01-01 --no-merges --name-only --pretty=format: -- httpie  (commits per file, top 25)" $ch

# ---- 7c. Duplication (hotspot ingredient; pylint instead of jscpd, so no npm) ----
Write-Host "[7c] Pylint: duplicated code blocks (this one takes a minute)" -ForegroundColor Cyan
$dup = & "$bin\pylint.exe" httpie --disable=all --enable=duplicate-code --min-similarity-lines=6 2>&1
Save-Log "$out\7c_pylint_duplicate_code.txt" "pylint httpie --disable=all --enable=duplicate-code --min-similarity-lines=6" $dup

# ---- 7d. pytest + coverage (own virtual environment on Python 3.12) --------------
# Python 3.14 is too new for some test dependencies, so this step uses Python 3.12.
Write-Host "[7d] pytest + coverage (several minutes the first time: it installs the test dependencies)" -ForegroundColor Cyan
$py312 = if ($Python312) { $Python312 } else { Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe" }
if (-not (Test-Path $py312)) {
  Write-Host "    skipped: Python 3.12 not found. Run again with -Python312 'C:\full\path\to\python.exe'" -ForegroundColor Yellow
} else {
  $pyt = Join-Path $TestVenv "Scripts\python.exe"
  if (-not (Test-Path $pyt)) { & $py312 -m venv $TestVenv }
  $inst = & $pyt -m pip install -q -e "${Repo}[test]" pytest-cov 2>&1
  Save-Log "$out\4b_pip_install_tests.txt" "pip install -e `"<repo>[test]`" pytest-cov   (Python 3.12 virtual environment)" $inst
  $ptOut = & $pyt -m pytest tests -q -p no:cacheprovider --override-ini=addopts= --cov=httpie "--cov-report=json:$out\coverage.json" --cov-report=term 2>&1
  Save-Log "$out\4b_pytest_coverage.txt" "python -m pytest tests -q -p no:cacheprovider --override-ini=addopts= --cov=httpie --cov-report=term   (last 80 lines)" ($ptOut | Select-Object -Last 80)
  $res = $ptOut | Where-Object { "$_" -match "\d+ passed|\d+ failed" } | Select-Object -Last 1
  $rows += [pscustomobject]@{ Check = "pytest (Python 3.12 venv)"; Expected = "1019 passed, 5 skipped, 4 xfailed"; YouGot = ("$res" -replace "\s+in [\d\.]+s.*", "" -replace ", \d+ warnings?", "") }
  $pc = "n/a"
  if (Test-Path "$out\coverage.json") {
    $val = & $pyt -c "import json,sys; print(round(json.load(open(sys.argv[1]))['totals']['percent_covered'], 1))" "$out\coverage.json" 2>&1
    $pc = "$val%"
  }
  $rows += [pscustomobject]@{ Check = "pytest-cov: line coverage of httpie"; Expected = "90.7%"; YouGot = $pc }
}

# ---- 7e. DSM and coupling (grimp): the original dsm.py, with outputs redirected here -----
Write-Host "[7e] DSM and coupling (grimp, matplotlib)" -ForegroundColor Cyan
$dsmSrc = Join-Path $Repo "track_a_analysis\scripts\dsm.py"
$pyt = Join-Path $TestVenv "Scripts\python.exe"
if (-not (Test-Path $dsmSrc)) {
  Write-Host "    skipped: $dsmSrc not found" -ForegroundColor Yellow
} elseif (-not (Test-Path $pyt)) {
  Write-Host "    skipped: the Python 3.12 environment from step 7d does not exist" -ForegroundColor Yellow
} else {
  $dinst = & $pyt -m pip install -q grimp matplotlib numpy 2>&1
  Save-Log "$out\9_dsm_pip_install.txt" "pip install grimp matplotlib numpy   (Python 3.12 virtual environment)" $dinst
  # same script as the original run; only ROOT is changed so that raw/ and figures/ are written next to this script
  $code = (Get-Content $dsmSrc -Raw).Replace('ROOT = Path(__file__).resolve().parents[1]', "ROOT = Path(r'$PSScriptRoot')")
  $tmp = Join-Path $env:TEMP "dsm_windows.py"
  [IO.File]::WriteAllText($tmp, $code, (New-Object Text.UTF8Encoding($false)))
  $dout = & $pyt $tmp 2>&1
  Save-Log "$out\9_dsm_run.txt" "python track_a_analysis\scripts\dsm.py   (copy with output folders redirected to track_a_analysis_windows)" $dout
  $dl = $dout | Where-Object { "$_" -match "modules=\d+ edges=\d+" } | Select-Object -Last 1
  $dres = "n/a"
  if ("$dl" -match "modules=(\d+) edges=(\d+) .*sccs=(\d+)") { $dres = "$($Matches[1]) modules, $($Matches[2]) edges, $($Matches[3]) cycles" }
  $rows += [pscustomobject]@{ Check = "grimp DSM: import graph"; Expected = "78 modules, 208 edges, 3 cycles"; YouGot = $dres }
}

# ---- 8. Code snippets the report talks about (with line numbers) ---------------
Write-Host "[8] Saving code snippets with line numbers" -ForegroundColor Cyan
function Snip([string]$file, [int]$from, [int]$to, [string]$why) {
  $p = Join-Path $Repo $file
  $res = @("", "=== $file  lines ${from}-${to}  :  $why ===")
  if (Test-Path $p) {
    $all = Get-Content $p
    for ($i = $from; $i -le [Math]::Min($to, $all.Count); $i++) { $res += ("{0,4}| {1}" -f $i, $all[$i - 1]) }
  } else { $res += "(file not found)" }
  return $res
}
$sn  = @()
$sn += Snip "httpie\core.py" 60 70  "bare 'raise' near line 67 (the Pylint E0704 false-positive case)"
$sn += Snip "httpie\core.py" 84 110 "duplicated KeyboardInterrupt / SystemExit handlers (lines ~86-90 and ~104-108)"
$sn += Snip "httpie\internal\update_warnings.py" 38 50 "requests.get(..., verify=False) near line 44"
$sn += Snip "httpie\ssl_.py" 1 40 "file SonarQube flagged with S930 (check the flagged call yourself)"
Save-Log "$out\8_snippets.txt" "Get-Content with line numbers (see each section title)" $sn

# ---- summary ---------------------------------------------------------------------
Write-Host ""
Write-Host "Expected numbers come from the Track A report. Small differences can come from the" -ForegroundColor Yellow
Write-Host "platform or tool versions; that is worth a note, not a worry." -ForegroundColor Yellow
Write-Host ""
$table = $rows | Format-Table -AutoSize | Out-String
Write-Host $table
$table | Out-File -Encoding utf8 "$out\summary.txt"
Write-Host "Outputs saved in: $out"

param(
  [string]$RepoRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
  [int]$MaxAttempts = 5,
  [int]$SleepMilliseconds = 500
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($MaxAttempts -lt 1) {
  throw "MaxAttempts muss >= 1 sein."
}
if ($SleepMilliseconds -lt 0) {
  throw "SleepMilliseconds muss >= 0 sein."
}

$nextPath = Join-Path $RepoRoot "frontend\.next"
if (-not (Test-Path -LiteralPath $nextPath)) {
  Write-Host ".next Cleanup: Kein Verzeichnis gefunden unter $nextPath"
  exit 0
}

for ($attempt = 1; $attempt -le $MaxAttempts; $attempt += 1) {
  try {
    Remove-Item -LiteralPath $nextPath -Recurse -Force -ErrorAction Stop
    Write-Host ".next Cleanup: Verzeichnis entfernt ($nextPath)"
    exit 0
  } catch {
    if ($attempt -eq $MaxAttempts) {
      Write-Warning ".next Cleanup fehlgeschlagen nach $MaxAttempts Versuchen: $($_.Exception.Message)"
      Write-Warning "Bitte schliesse laufende Next.js-Terminals/Node-Prozesse und fuehre 'npm run stop:local' erneut aus."
      exit 0
    }
    Start-Sleep -Milliseconds $SleepMilliseconds
  }
}

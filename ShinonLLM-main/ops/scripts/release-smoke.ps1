Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-NpmCommand {
  $npm = Get-Command npm -ErrorAction SilentlyContinue
  if ($null -ne $npm -and -not [string]::IsNullOrWhiteSpace($npm.Source)) {
    return $npm.Source
  }

  $fallback = "C:\Program Files\nodejs\npm.cmd"
  if (Test-Path -LiteralPath $fallback -PathType Leaf) {
    return $fallback
  }

  throw "npm wurde nicht gefunden."
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$npmCmd = Resolve-NpmCommand

Push-Location $repoRoot
try {
  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $output = & $npmCmd run verify:full:node 2>&1
  $ErrorActionPreference = $previousErrorActionPreference
  $output | ForEach-Object { Write-Host $_ }

  if ($LASTEXITCODE -ne 0) {
    throw "verify:full:node failed with exit code $LASTEXITCODE"
  }

  $baselineLine = $output | Where-Object { $_ -match '^testline \| ' } | Select-Object -Last 1
  if ([string]::IsNullOrWhiteSpace($baselineLine)) {
    throw "Baseline testline wurde nicht gefunden."
  }

  $utcStamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $snippet = @(
    "## Smoke Snapshot",
    "- Date (UTC): $utcStamp",
    "- Verify: npm run verify:full:node PASS",
    "- Baseline: $baselineLine"
  )

  $snippet -join "`n"
}
finally {
  Pop-Location
}

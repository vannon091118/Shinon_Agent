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

$repoRoot = if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) { $PSScriptRoot } else { (Get-Location).Path }
$npmCmd = Resolve-NpmCommand

Push-Location $repoRoot
try {
  & $npmCmd run verify:full:node
}
finally {
  Pop-Location
}

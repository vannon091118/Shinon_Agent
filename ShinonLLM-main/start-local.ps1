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

  throw "npm wurde nicht gefunden. Installiere Node.js oder fuege npm zu PATH hinzu."
}

function Convert-ToSingleQuotedPsLiteral {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Value
  )

  return "'" + $Value.Replace("'", "''") + "'"
}

function Start-ShinonLocalStack {
  [CmdletBinding()]
  param()

  $repoRoot = if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    $PSScriptRoot
  } else {
    (Get-Location).Path
  }

  $npmCommand = Resolve-NpmCommand
  $backendPath = Join-Path $repoRoot "backend"
  $frontendPath = Join-Path $repoRoot "frontend"
  $stopScriptPath = Join-Path $repoRoot "stop-local.ps1"

  if (-not (Test-Path -LiteralPath $backendPath -PathType Container)) {
    throw "Backend-Verzeichnis fehlt: $backendPath"
  }
  if (-not (Test-Path -LiteralPath $frontendPath -PathType Container)) {
    throw "Frontend-Verzeichnis fehlt: $frontendPath"
  }

  $backendPathLiteral = Convert-ToSingleQuotedPsLiteral -Value $backendPath
  $frontendPathLiteral = Convert-ToSingleQuotedPsLiteral -Value $frontendPath
  $npmLiteral = Convert-ToSingleQuotedPsLiteral -Value $npmCommand
  $stopLiteral = Convert-ToSingleQuotedPsLiteral -Value $stopScriptPath

  $backendCmd = @"
Set-Location -LiteralPath $backendPathLiteral
Register-EngineEvent PowerShell.Exiting -Action { & $stopLiteral | Out-Null } | Out-Null
try {
  & $npmLiteral run start
} finally {
  & $stopLiteral | Out-Null
}
"@

  $frontendCmd = @"
Set-Location -LiteralPath $frontendPathLiteral
Register-EngineEvent PowerShell.Exiting -Action { & $stopLiteral | Out-Null } | Out-Null
try {
  & $npmLiteral run dev
} finally {
  & $stopLiteral | Out-Null
}
"@

  $llamacppScript = Join-Path $repoRoot "ops\scripts\start-llamacpp.ps1"
  if (Test-Path -LiteralPath $llamacppScript -PathType Leaf) {
    Write-Host "Starte llama.cpp Infrastruktur..."
    try {
      & $llamacppScript -ModelFile 'qwen2.5-0.5b-instruct-q4_k_m.gguf' -Port 8000 -HealthTimeout 120
    } catch {
      Write-Warning "llama.cpp konnte nicht gestartet werden: $($_.Exception.Message)"
      Write-Host "Fahre ohne llama.cpp fort (Ollama-Modus)..."
    }
  } else {
    Write-Host "llama.cpp Script nicht gefunden, fahre ohne lokales LLM fort..."
  }

  Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $backendCmd
  ) | Out-Null

  Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $frontendCmd
  ) | Out-Null

  Write-Host "Lokaler Stack gestartet:"
  Write-Host "- Backend:  http://127.0.0.1:3001"
  Write-Host "- Frontend: http://127.0.0.1:3000"
}

if ($MyInvocation.InvocationName -ne ".") {
  try {
    Start-ShinonLocalStack
  } catch {
    Write-Error $_
    exit 1
  }
}

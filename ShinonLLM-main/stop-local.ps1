Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ports = @(3000, 3001)
$connections = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object {
  $ports -contains $_.LocalPort
})

if ($null -eq $connections -or $connections.Count -eq 0) {
  Write-Host "Keine Listener auf Ports 3000/3001 gefunden."
} else {
  $processIds = $connections.OwningProcess | Sort-Object -Unique
  foreach ($processId in $processIds) {
    try {
      $process = Get-Process -Id $processId -ErrorAction Stop
      Stop-Process -Id $processId -Force
      Write-Host "Beendet: PID $processId ($($process.ProcessName))"
    } catch {
      Write-Warning "Konnte PID $processId nicht beenden: $($_.Exception.Message)"
    }
  }

  Write-Host "Ports 3000/3001 sind jetzt frei."
}

$cleanupScript = Join-Path $PSScriptRoot "ops\scripts\cleanup-frontend-next.ps1"
if (-not (Test-Path -LiteralPath $cleanupScript -PathType Leaf)) {
  Write-Warning "Cleanup-Skript nicht gefunden: $cleanupScript"
  exit 0
}

try {
  & $cleanupScript -RepoRoot $PSScriptRoot
} catch {
  Write-Warning ".next Cleanup konnte nicht gestartet werden: $($_.Exception.Message)"
  Write-Warning "Bitte schliesse laufende Next.js-Terminals/Node-Prozesse und fuehre 'npm run stop:local' erneut aus."
}

Write-Host "Lokaler Stop abgeschlossen."

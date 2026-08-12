Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Verfügbare Test-Modelle (klein, für Entwicklung)
$AVAILABLE_MODELS = @{
  'tinyllama-1.1b.Q4_K_M.gguf' = @{
    Url = 'https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf'
    Size = '~640MB'
    Description = 'TinyLlama 1.1B - Q4 Kompression (empfohlen für Tests)'
  }
  'tinyllama-1.1b.Q5_K_S.gguf' = @{
    Url = 'https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q5_K_S.gguf'
    Size = '~800MB'
    Description = 'TinyLlama 1.1B - Q5 Kompression (besserer Quality)'
  }
  'qwen2.5-0.5b.Q4_K_M.gguf' = @{
    Url = 'https://huggingface.co/TheBloke/Qwen2-0.5B-Instruct-GGUF/resolve/main/qwen2-0.5b-instruct-q4_k_m.gguf'
    Size = '~420MB'
    Description = 'Qwen2 0.5B - Q4 Kompression (kleiner, schneller)'
  }
}

function Get-ModelPath {
  param([string]$ModelFile)
  
  $appDataPath = Join-Path $env:LOCALAPPDATA "ShinonLLM\models"
  $repoRoot = Join-Path $PSScriptRoot '..\..'
  $repoModelPath = Join-Path $repoRoot "models\$ModelFile"
  
  # Prüfe AppData zuerst
  $appDataModelPath = Join-Path $appDataPath $ModelFile
  if (Test-Path -LiteralPath $appDataModelPath -PathType Leaf) {
    return $appDataModelPath
  }
  
  # Fallback: Projektverzeichnis
  if (Test-Path -LiteralPath $repoModelPath -PathType Leaf) {
    return $repoModelPath
  }
  
  return $null
}

function Install-Model {
  param(
    [string]$ModelFile,
    [string]$Url
  )
  
  $appDataPath = Join-Path $env:LOCALAPPDATA "ShinonLLM\models"
  
  # Erstelle Verzeichnis wenn nicht vorhanden
  if (-not (Test-Path -LiteralPath $appDataPath -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $appDataPath | Out-Null
  }
  
  $downloadPath = Join-Path $appDataPath $ModelFile
  
  Write-Host "Lade Model herunter: $ModelFile"
  Write-Host "Ziel: $downloadPath"
  
  try {
    Invoke-WebRequest -Uri $Url -OutFile $downloadPath -UseBasicParsing -ProgressPreference 'SilentlyContinue'
    Write-Host "✓ Model erfolgreich heruntergeladen!" -ForegroundColor Green
    return $downloadPath
  } catch {
    throw "Download fehlgeschlagen: $($_.Exception.Message)"
  }
}

function Show-ModelMenu {
  Write-Host "`n=== Verfügbare Modelle ===" -ForegroundColor Cyan
  $i = 1
  foreach ($key in $AVAILABLE_MODELS.Keys) {
    $model = $AVAILABLE_MODELS[$key]
    Write-Host "$i. $key ($($model.Size))"
    Write-Host "   → $($model.Description)"
    $i++
  }
  Write-Host ""
  
  $selection = Read-Host "Model-Nummer auswählen (1-$($AVAILABLE_MODELS.Count)) oder Enter für Standard (1)"
  
  if ([string]::IsNullOrWhiteSpace($selection) -or $selection -eq "1") {
    return 'tinyllama-1.1b.Q4_K_M.gguf'
  }
  
  $idx = [int]$selection - 1
  if ($idx -ge 0 -and $idx -lt $AVAILABLE_MODELS.Count) {
    return $AVAILABLE_MODELS.Keys[$idx]
  }
  
  return 'tinyllama-1.1b.Q4_K_M.gguf'
}

function Start-LlamaCppServer {
  [CmdletBinding()]
  param(
    [string]$ModelFile = 'tinyllama-1.1b.Q4_K_M.gguf',
    [int]$Port = 8000,
    [int]$HealthTimeout = 60,
    [switch]$AutoDownload
  )

  $repoRoot = Join-Path $PSScriptRoot '..\..'
  $appDataPath = Join-Path $env:LOCALAPPDATA "ShinonLLM\models"
  
  # Model suchen
  $modelPath = Get-ModelPath -ModelFile $ModelFile
  
  # Wenn nicht gefunden → Download anbieten
  if ($null -eq $modelPath) {
    Write-Host "`n⚠ Model nicht gefunden: $ModelFile" -ForegroundColor Yellow
    Write-Host "Suchpfade:"
    Write-Host "  - $appDataPath"
    Write-Host "  - $repoRoot\models"
    
    if ($AutoDownload) {
      # Auto-Download mit Standard-Modell
      if ($AVAILABLE_MODELS.ContainsKey($ModelFile)) {
        $modelInfo = $AVAILABLE_MODELS[$ModelFile]
        $modelPath = Install-Model -ModelFile $ModelFile -Url $modelInfo.Url
      } else {
        $ModelFile = 'tinyllama-1.1b.Q4_K_M.gguf'
        $modelInfo = $AVAILABLE_MODELS[$ModelFile]
        $modelPath = Install-Model -ModelFile $ModelFile -Url $modelInfo.Url
      }
    } else {
      Write-Host "`nModel herunterladen? (j/n)" -ForegroundColor Cyan
      $answer = Read-Host "Standard: j"
      if ($answer -eq 'j' -or [string]::IsNullOrWhiteSpace($answer)) {
        $ModelFile = Show-ModelMenu
        $modelInfo = $AVAILABLE_MODELS[$ModelFile]
        $modelPath = Install-Model -ModelFile $ModelFile -Url $modelInfo.Url
      } else {
        throw "Model nicht gefunden. Bitte manuell herunterladen und in $appDataPath ablegen."
      }
    }
  } else {
    Write-Host "✓ Model gefunden: $modelPath" -ForegroundColor Green
  }

  Write-Host "Checking for llama-server.exe or using Docker fallback..."
  
  # Try to find llama-server.exe in common places
  $llamaBinary = Get-Command llama-server.exe -ErrorAction SilentlyContinue
  
  if ($null -ne $llamaBinary) {
    Write-Host "Starting local llama-server.exe binary..."
    $serverCmd = "& $($llamaBinary.Source) -m '$modelPath' --port $Port --host 0.0.0.0 -n 512"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $serverCmd
  } else {
    Write-Host "llama-server.exe not found in PATH. Using Docker fallback (ghcr.io/ggerganov/llama.cpp:server)..."
    $composeFile = Join-Path $repoRoot "ops\docker-compose.local.yml"
    
    if (-not (Test-Path -LiteralPath $composeFile -PathType Leaf)) {
      throw "Docker compose file not found at $composeFile"
    }
    
    # Start only the llamacpp service
    $env:LLAMACPP_MODEL_FILE = $ModelFile
    $dockerCmd = "docker compose -f '$composeFile' -p llmrab-local up -d llamacpp"
    Invoke-Expression $dockerCmd
  }

  # Wait for health check
  Write-Host "Waiting for llama.cpp server to become healthy on port $Port..."
  $healthUrl = "http://127.0.0.1:$Port/health"
  $deadline = (Get-Date).AddSeconds($HealthTimeout)
  
  while ((Get-Date) -lt $deadline) {
    try {
      $resp = Invoke-RestMethod -Uri $healthUrl -Method Get -ErrorAction Stop
      if ($resp.status -eq 'ok' -or $resp.ok -eq $true) {
        Write-Host "llama.cpp is READY." -ForegroundColor Green
        return
      }
    } catch {
      # Ignore connection errors while waiting
    }
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 2
  }
  
  throw "llama.cpp did not become healthy within $HealthTimeout seconds."
}

if ($MyInvocation.InvocationName -ne '.') {
  try {
    Start-LlamaCppServer -AutoDownload:$true
  } catch {
    Write-Error $_
    exit 1
  }
}

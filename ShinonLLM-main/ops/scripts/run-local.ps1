Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Start-LocalStack {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $false)]
    [object]$LocalRuntimeConfig = $null
  )

  $scriptRoot = Split-Path -Parent $PSCommandPath
  $defaultComposeFilePath = Join-Path $scriptRoot '..\docker-compose.local.yml'
  $defaultComposeFilePath = [System.IO.Path]::GetFullPath($defaultComposeFilePath)

  $composeFilePath = $defaultComposeFilePath
  $projectName = 'llmrab-local'
  $healthTimeoutSeconds = 120
  $pollIntervalSeconds = 2

  if ($null -ne $LocalRuntimeConfig) {
    if ($LocalRuntimeConfig -is [string]) {
      $composeFilePath = [System.IO.Path]::GetFullPath($LocalRuntimeConfig)
    } elseif ($LocalRuntimeConfig -is [hashtable] -or $LocalRuntimeConfig -is [pscustomobject]) {
      $configObject = [pscustomobject]$LocalRuntimeConfig

      if ($configObject.PSObject.Properties.Match('ComposeFilePath').Count -gt 0 -and -not [string]::IsNullOrWhiteSpace([string]$configObject.ComposeFilePath)) {
        $composeFilePath = [System.IO.Path]::GetFullPath([string]$configObject.ComposeFilePath)
      }

      if ($configObject.PSObject.Properties.Match('ProjectName').Count -gt 0 -and -not [string]::IsNullOrWhiteSpace([string]$configObject.ProjectName)) {
        $projectName = [string]$configObject.ProjectName
      }

      if ($configObject.PSObject.Properties.Match('HealthTimeoutSeconds').Count -gt 0) {
        $healthTimeoutSeconds = [int]$configObject.HealthTimeoutSeconds
      }

      if ($configObject.PSObject.Properties.Match('PollIntervalSeconds').Count -gt 0) {
        $pollIntervalSeconds = [int]$configObject.PollIntervalSeconds
      }
    } else {
      throw 'Invalid local runtime config: expected string, hashtable, or pscustomobject'
    }
  }

  if ($healthTimeoutSeconds -lt 1) {
    throw 'Invalid local runtime config: HealthTimeoutSeconds must be greater than zero'
  }

  if ($pollIntervalSeconds -lt 1) {
    throw 'Invalid local runtime config: PollIntervalSeconds must be greater than zero'
  }

  if (-not (Test-Path -LiteralPath $composeFilePath -PathType Leaf)) {
    throw "Missing dependency: compose file not found at '$composeFilePath'"
  }

  $modelFileName = if (-not [string]::IsNullOrWhiteSpace($env:LLAMACPP_MODEL_FILE)) {
    [string]$env:LLAMACPP_MODEL_FILE
  } else {
    'qwen2.5-0.5b-instruct-q4_k_m.gguf'
  }
  $modelDir = Join-Path (Split-Path -Parent $composeFilePath) 'models'
  $modelPath = Join-Path $modelDir $modelFileName
  if (-not (Test-Path -LiteralPath $modelPath -PathType Leaf)) {
    throw "Missing llama.cpp model file: '$modelPath'. Download a GGUF model into ops\\models first."
  }

  $dockerCommand = Get-Command -Name docker -ErrorAction Stop
  if ($null -eq $dockerCommand) {
    throw 'Missing dependency: docker command is not available'
  }

  $startTimestamp = [DateTime]::UtcNow
  $upArgs = @('compose', '-f', $composeFilePath, '-p', $projectName, 'up', '-d', '--build')
  & $dockerCommand @upArgs | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Local stack start failed with exit code $LASTEXITCODE"
  }

  $deadline = [DateTime]::UtcNow.AddSeconds($healthTimeoutSeconds)
  $lastServiceSnapshot = @()

  while ($true) {
    $psArgs = @('compose', '-f', $composeFilePath, '-p', $projectName, 'ps', '--format', 'json')
    $rawStatus = & $dockerCommand @psArgs
    if ($LASTEXITCODE -ne 0) {
      throw "Local stack status check failed with exit code $LASTEXITCODE"
    }

    if ([string]::IsNullOrWhiteSpace($rawStatus)) {
      $services = @()
    } else {
      try {
        $services = $rawStatus | ConvertFrom-Json
      } catch {
        throw 'Local stack status payload is not valid JSON'
      }
    }

    if ($services -isnot [System.Collections.IEnumerable] -or $services -is [string]) {
      $services = @($services)
    }

    $lastServiceSnapshot = @()
    $allReady = $true

    foreach ($service in $services) {
      if ($null -eq $service) {
        $allReady = $false
        continue
      }

      $serviceName = if ($service.PSObject.Properties.Match('Service').Count -gt 0 -and -not [string]::IsNullOrWhiteSpace([string]$service.Service)) {
        [string]$service.Service
      } elseif ($service.PSObject.Properties.Match('Name').Count -gt 0 -and -not [string]::IsNullOrWhiteSpace([string]$service.Name)) {
        [string]$service.Name
      } else {
        'unknown'
      }

      $state = if ($service.PSObject.Properties.Match('State').Count -gt 0) {
        [string]$service.State
      } else {
        ''
      }

      $health = if ($service.PSObject.Properties.Match('Health').Count -gt 0) {
        [string]$service.Health
      } else {
        ''
      }

      $isReady = $state -eq 'running' -and ($health -eq '' -or $health -eq 'healthy')
      if (-not $isReady) {
        $allReady = $false
      }

      $lastServiceSnapshot += [pscustomobject]@{
        Service = $serviceName
        State   = $state
        Health  = $health
        Ready   = $isReady
      }
    }

    if ($services.Count -gt 0 -and $allReady) {
      return [pscustomobject]@{
        ComposeFilePath   = $composeFilePath
        ProjectName       = $projectName
        StartedAt         = $startTimestamp
        CheckedAt         = [DateTime]::UtcNow
        HealthTimeoutSecs  = $healthTimeoutSeconds
        PollIntervalSecs   = $pollIntervalSeconds
        Services          = $lastServiceSnapshot
      }
    }

    if ([DateTime]::UtcNow -ge $deadline) {
      throw "Local stack did not become healthy within $healthTimeoutSeconds seconds"
    }

    Start-Sleep -Seconds $pollIntervalSeconds
  }
}

if ($MyInvocation.InvocationName -ne '.') {
  try {
    Start-LocalStack | Out-Host
  } catch {
    Write-Error $_
    exit 1
  }
}

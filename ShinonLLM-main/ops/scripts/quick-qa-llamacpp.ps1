Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-LlamaCppQuickQa {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $false)]
    [string]$Endpoint = 'http://127.0.0.1:8000/v1/chat/completions',

    [Parameter(Mandatory = $false)]
    [string]$Model = 'qwen2.5-0.5b-instruct-q4_k_m',

    [Parameter(Mandatory = $false)]
    [string]$Prompt = 'Antworte in einem Satz: Wofuer ist ShinonLLM gedacht?'
  )

  $payload = @{
    model = $Model
    messages = @(
      @{
        role = 'system'
        content = 'Du bist ein praeziser lokaler QA-Assistent.'
      },
      @{
        role = 'user'
        content = $Prompt
      }
    )
    temperature = 0.2
    max_tokens = 120
    stream = $false
  } | ConvertTo-Json -Depth 8

  $response = Invoke-RestMethod -Method Post -Uri $Endpoint -ContentType 'application/json; charset=utf-8' -Body $payload -TimeoutSec 60
  $message = $response.choices[0].message.content

  if ([string]::IsNullOrWhiteSpace([string]$message)) {
    throw 'Quick QA failed: llama.cpp response had no assistant message content.'
  }

  [pscustomobject]@{
    Endpoint = $Endpoint
    Model = $Model
    Reply = [string]$message
  }
}

if ($MyInvocation.InvocationName -ne '.') {
  try {
    Invoke-LlamaCppQuickQa | Format-List
  } catch {
    Write-Error $_
    exit 1
  }
}

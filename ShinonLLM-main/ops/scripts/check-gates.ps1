function Invoke-GateChecks {
    [CmdletBinding()]
    param(
        [Parameter(ValueFromPipeline = $true)]
        [AllowNull()]
        [object]$RuntimeConfig = @{}
    )

    begin {
        $scriptPath = $PSCommandPath
        if ([string]::IsNullOrWhiteSpace($scriptPath)) {
            $scriptPath = $MyInvocation.MyCommand.Path
        }

        if ([string]::IsNullOrWhiteSpace($scriptPath)) {
            throw "Unable to resolve script path"
        }

        $scriptDir = Split-Path -Parent $scriptPath
        $repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
        $defaultMatrixPath = Join-Path $repoRoot 'docs\validation\MATRIX__VALIDATION_GATES.md'
        $defaultTargetPath = $scriptPath
    }

    process {
        if ($null -eq $RuntimeConfig) {
            $RuntimeConfig = @{}
        }

        if ($RuntimeConfig -is [System.Collections.IDictionary]) {
            $config = @{}
            foreach ($key in $RuntimeConfig.Keys) {
                $config[$key] = $RuntimeConfig[$key]
            }
        }
        else {
            $config = @{}
            $properties = $RuntimeConfig.PSObject.Properties
            foreach ($property in $properties) {
                $config[$property.Name] = $property.Value
            }
        }

        $matrixPath = if ($config.ContainsKey('MatrixPath') -and -not [string]::IsNullOrWhiteSpace([string]$config.MatrixPath)) {
            [string]$config.MatrixPath
        }
        else {
            $defaultMatrixPath
        }

        $targetPath = if ($config.ContainsKey('TargetPath') -and -not [string]::IsNullOrWhiteSpace([string]$config.TargetPath)) {
            [string]$config.TargetPath
        }
        else {
            $defaultTargetPath
        }

        $requiredBlueprintId = if ($config.ContainsKey('BlueprintId') -and -not [string]::IsNullOrWhiteSpace([string]$config.BlueprintId)) {
            [string]$config.BlueprintId
        }
        else {
            'BP__ops__ops_scripts_check_gates_ps1'
        }

        $requiredGateId = if ($config.ContainsKey('GateId') -and -not [string]::IsNullOrWhiteSpace([string]$config.GateId)) {
            [string]$config.GateId
        }
        else {
            'GATE_AUTOMATION'
        }

        $checks = [System.Collections.Generic.List[string]]::new()

        if (-not (Test-Path -LiteralPath $matrixPath)) {
            throw "Missing validation matrix: $matrixPath"
        }
        $checks.Add("matrix_exists:$matrixPath")

        if (-not (Test-Path -LiteralPath $targetPath)) {
            throw "Missing target script: $targetPath"
        }
        $checks.Add("target_exists:$targetPath")

        $matrixContent = Get-Content -LiteralPath $matrixPath -Raw
        if ($matrixContent -notmatch [regex]::Escape($requiredBlueprintId)) {
            throw "Validation matrix does not reference blueprint id: $requiredBlueprintId"
        }
        $checks.Add("matrix_blueprint:$requiredBlueprintId")

        if ($matrixContent -notmatch [regex]::Escape($requiredGateId)) {
            throw "Validation matrix does not reference gate id: $requiredGateId"
        }
        $checks.Add("matrix_gate:$requiredGateId")

        $targetContent = Get-Content -LiteralPath $targetPath -Raw
        if ($targetContent -notmatch 'function\s+Invoke-GateChecks\b') {
            throw "Required symbol missing: Invoke-GateChecks"
        }
        $checks.Add("symbol:Invoke-GateChecks")

        [pscustomobject]@{
            Status = 'PASS'
            BlueprintId = $requiredBlueprintId
            GateId = $requiredGateId
            MatrixPath = $matrixPath
            TargetPath = $targetPath
            Checks = $checks.ToArray()
        }
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        $result = Invoke-GateChecks -RuntimeConfig @{}
        $result | ConvertTo-Json -Depth 5 -Compress
        exit 0
    }
    catch {
        Write-Error $_
        exit 1
    }
}

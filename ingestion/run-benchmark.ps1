param(
    [string]$ComposeFile = "docker/docker-compose.yml",
    [string]$PythonExe = "c:/vs code/UniGRAPH2/.venv/Scripts/python.exe",
    [int]$Count = 5000,
    [int]$TimeoutSeconds = 240,
    [string]$JobManagerUrl = "http://localhost:8082"
)

$ErrorActionPreference = "Stop"

function Wait-Http {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                return
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }

    throw "Timed out waiting for $Url"
}

function Set-ProfileEnv {
    param([string]$Profile)

    if ($Profile -eq "baseline") {
        $env:ENRICH_PARALLELISM = "1"
        $env:ANOMALY_PARALLELISM = "1"
        $env:MIN_PAUSE_BETWEEN_CHECKPOINTS_MS = "0"
        $env:ENABLE_UNALIGNED_CHECKPOINTS = "false"
        $env:ENRICH_STATE_BACKEND = "ROCKSDB"
        $env:KAFKA_PRODUCER_LINGER_MS = "50"
        $env:KAFKA_PRODUCER_COMPRESSION_TYPE = "none"
    } elseif ($Profile -eq "optimized") {
        $env:ENRICH_PARALLELISM = "12"
        $env:ANOMALY_PARALLELISM = "12"
        $env:MIN_PAUSE_BETWEEN_CHECKPOINTS_MS = "5000"
        $env:ENABLE_UNALIGNED_CHECKPOINTS = "true"
        $env:ENRICH_STATE_BACKEND = "HASHMAP"
        $env:KAFKA_PRODUCER_LINGER_MS = "2"
        $env:KAFKA_PRODUCER_COMPRESSION_TYPE = "lz4"
    } else {
        throw "Unsupported profile: $Profile"
    }
}

function Invoke-ProfileRun {
    param([string]$Profile)

    Write-Host "`n=== Running profile: $Profile ==="
    Set-ProfileEnv -Profile $Profile

    docker compose -f $ComposeFile up -d --force-recreate flink-jobmanager flink-taskmanager | Out-Null
    Wait-Http -Url "$JobManagerUrl/overview" -TimeoutSeconds 240

    powershell -NoProfile -ExecutionPolicy Bypass -File ingestion/run-e2e-ingestion.ps1 | Out-Null

    $json = & $PythonExe ingestion/benchmark_ingestion.py --bootstrap localhost:19092 --count $Count --timeout $TimeoutSeconds --profile $Profile
    $result = ($json | Select-Object -Last 1) | ConvertFrom-Json
    return $result
}

$env:JAVA_HOME = [Environment]::GetEnvironmentVariable("JAVA_HOME", "User")
$env:MAVEN_HOME = [Environment]::GetEnvironmentVariable("MAVEN_HOME", "User")
$env:Path = "$env:JAVA_HOME\bin;$env:MAVEN_HOME\bin;$env:Path"

$baseline = Invoke-ProfileRun -Profile "baseline"
$optimized = Invoke-ProfileRun -Profile "optimized"

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outPath = "ingestion/benchmark-results-$timestamp.json"
@($baseline, $optimized) | ConvertTo-Json -Depth 6 | Set-Content -Path $outPath -Encoding UTF8

Write-Output "`n=== Throughput and Latency Comparison ==="
$table = @(
    [PSCustomObject]@{
        Profile = $baseline.profile
        Status = $baseline.status
        Count = $baseline.count
        EnrichedTPS = $baseline.throughput_tps
        P95ms = $baseline.latency_ms.p95
        P99ms = $baseline.latency_ms.p99
        MissingEnriched = $baseline.missing_enriched
        MissingRule = $baseline.missing_rule
    },
    [PSCustomObject]@{
        Profile = $optimized.profile
        Status = $optimized.status
        Count = $optimized.count
        EnrichedTPS = $optimized.throughput_tps
        P95ms = $optimized.latency_ms.p95
        P99ms = $optimized.latency_ms.p99
        MissingEnriched = $optimized.missing_enriched
        MissingRule = $optimized.missing_rule
    }
)

$table | Format-Table -AutoSize
Write-Output "Results written to $outPath"

param(
    [string]$ComposeFile = "docker/docker-compose.yml",
    [string]$JobManagerUrl = "http://localhost:8082",
    [string]$JarPath = "ingestion/flink/target/unigraph-ingestion-jobs.jar",
    [string]$PythonExe = "c:/vs code/UniGRAPH2/.venv/Scripts/python.exe"
)

$ErrorActionPreference = "Stop"

function Wait-Http {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 120
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

function Ensure-Topics {
    docker exec kafka-1 kafka-topics --create --if-not-exists --bootstrap-server kafka-1:9092 --topic raw-transactions --partitions 12 --replication-factor 3 --config retention.ms=604800000 | Out-Null
    docker exec kafka-1 kafka-topics --create --if-not-exists --bootstrap-server kafka-1:9092 --topic enriched-transactions --partitions 12 --replication-factor 3 --config retention.ms=604800000 | Out-Null
    docker exec kafka-1 kafka-topics --create --if-not-exists --bootstrap-server kafka-1:9092 --topic rule-violations --partitions 6 --replication-factor 3 --config retention.ms=259200000 | Out-Null
}

function Ensure-ConfluentKafka {
    $hasPkg = & $PythonExe -c "import importlib.util; print(importlib.util.find_spec('confluent_kafka') is not None)"
    if ($hasPkg.Trim().ToLower() -ne "true") {
        & $PythonExe -m pip install confluent-kafka
    }
}

function Build-Jar {
    $env:JAVA_HOME = [Environment]::GetEnvironmentVariable("JAVA_HOME", "User")
    $env:MAVEN_HOME = [Environment]::GetEnvironmentVariable("MAVEN_HOME", "User")
    $env:Path = "$env:JAVA_HOME\bin;$env:MAVEN_HOME\bin;$env:Path"
    mvn -f ingestion/flink/pom.xml -DskipTests package
}

function Deploy-Jobs {
    $overview = Invoke-RestMethod -Method Get -Uri "$JobManagerUrl/jobs/overview"
    foreach ($job in $overview.jobs) {
        if ($job.state -ne "CANCELED") {
            Invoke-RestMethod -Method Patch -Uri "$JobManagerUrl/jobs/$($job.jid)" | Out-Null
        }
    }

    # Wait for in-flight cancellations so we do not race verification against older jobs.
    $cancelDeadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $cancelDeadline) {
        $remaining = (Invoke-RestMethod -Method Get -Uri "$JobManagerUrl/jobs/overview").jobs |
            Where-Object { $_.state -ne "CANCELED" }
        if ($remaining.Count -eq 0) {
            break
        }
        Start-Sleep -Seconds 2
    }

    $uploadJson = (curl.exe -s -X POST -H "Expect:" -F "jarfile=@$JarPath" "$JobManagerUrl/jars/upload" | ConvertFrom-Json)
    $jarId = [System.IO.Path]::GetFileName($uploadJson.filename)

    $entryClasses = @("TransactionEnrichmentJob", "AnomalyWindowJob")
    $submittedJobIds = @()
    foreach ($entryClass in $entryClasses) {
        $payload = @{entryClass = $entryClass} | ConvertTo-Json -Compress
        $runResponse = Invoke-RestMethod -Method Post -Uri "$JobManagerUrl/jars/$jarId/run" -ContentType "application/json" -Body $payload
        if ($null -eq $runResponse.jobid -or [string]::IsNullOrWhiteSpace($runResponse.jobid)) {
            throw "Failed to submit Flink entry class $entryClass"
        }
        $submittedJobIds += $runResponse.jobid
    }

    return $submittedJobIds
}

function Wait-RunningJobs {
    param(
        [string[]]$JobIds,
        [int]$TimeoutSeconds = 120
    )

    if ($null -eq $JobIds -or $JobIds.Count -eq 0) {
        throw "Wait-RunningJobs called without submitted job IDs"
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $allRunning = $true
        foreach ($jobId in $JobIds) {
            $job = Invoke-RestMethod -Method Get -Uri "$JobManagerUrl/jobs/$jobId"
            if ($job.state -eq "RUNNING") {
                continue
            }
            if ($job.state -eq "FAILED" -or $job.state -eq "CANCELED" -or $job.state -eq "FINISHED") {
                throw "Flink job $jobId entered terminal state $($job.state) before verification"
            }
            $allRunning = $false
            break
        }

        if ($allRunning) {
            return
        }
        Start-Sleep -Seconds 2
    }

    throw "Timed out waiting for both Flink jobs to be RUNNING"
}

function Publish-And-Verify {
    $resultJson = & $PythonExe ingestion/verify_e2e_ingestion.py --bootstrap localhost:19092 --timeout-enriched 90 --timeout-rule 150
    $result = $resultJson | ConvertFrom-Json
    if ($result.status -ne "PASS") {
        throw "E2E failed: $($result.error)"
    }
    return $result
}

Write-Output "[1/6] Starting ingestion services"
docker compose -f $ComposeFile up -d zookeeper kafka-1 kafka-2 kafka-3 flink-jobmanager flink-taskmanager | Out-Null

Write-Output "[2/6] Waiting for Flink API and Kafka"
Wait-Http -Url "$JobManagerUrl/overview" -TimeoutSeconds 180
Start-Sleep -Seconds 8

Write-Output "[3/6] Creating ingestion topics"
Ensure-Topics

Write-Output "[4/6] Building Flink jobs"
Build-Jar

Write-Output "[5/6] Deploying Flink jobs"
$submittedJobIds = Deploy-Jobs
Wait-RunningJobs -JobIds $submittedJobIds -TimeoutSeconds 180

Write-Output "[6/6] Publishing and verifying flow"
Ensure-ConfluentKafka
$result = Publish-And-Verify
$result | ConvertTo-Json -Depth 4 | Write-Output

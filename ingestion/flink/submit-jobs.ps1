param(
    [string]$JobManagerUrl = "http://localhost:8082",
    [string]$JarPath = "ingestion/flink/target/unigraph-ingestion-jobs.jar"
)

if (-not (Test-Path $JarPath)) {
    throw "Jar not found at '$JarPath'. Build first with: mvn -f ingestion/flink/pom.xml -DskipTests package"
}

$uploadResponse = curl.exe -s -X POST -H "Expect:" -F "jarfile=@$JarPath" "$JobManagerUrl/jars/upload"
if (-not $uploadResponse) {
    throw "Failed to upload jar to Flink JobManager at $JobManagerUrl"
}

$uploadJson = $uploadResponse | ConvertFrom-Json
if (-not $uploadJson.filename) {
    throw "Unexpected upload response: $uploadResponse"
}

$jarId = [System.IO.Path]::GetFileName($uploadJson.filename)
Write-Output "Uploaded jar id: $jarId"

$jobs = @(
    "TransactionEnrichmentJob",
    "AnomalyWindowJob"
)

foreach ($jobClass in $jobs) {
    $payload = @{ entryClass = $jobClass } | ConvertTo-Json -Compress
    $runResponse = Invoke-RestMethod -Method Post -Uri "$JobManagerUrl/jars/$jarId/run" -ContentType "application/json" -Body $payload
    Write-Output "Submitted $jobClass"
    $runResponse | ConvertTo-Json -Compress | Write-Output
}

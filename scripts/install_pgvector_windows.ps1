$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SourceRoot = Join-Path $ProjectRoot "data\tools\pgvector-pg16"
$PostgresRoot = "C:\Program Files\PostgreSQL\16"

Copy-Item -Path (Join-Path $SourceRoot "lib\vector.dll") `
    -Destination (Join-Path $PostgresRoot "lib\vector.dll") `
    -Force

Copy-Item -Path (Join-Path $SourceRoot "share\extension\vector*") `
    -Destination (Join-Path $PostgresRoot "share\extension") `
    -Force

Copy-Item -Path (Join-Path $SourceRoot "include\server\extension\vector") `
    -Destination (Join-Path $PostgresRoot "include\server\extension") `
    -Recurse `
    -Force

Write-Host "pgvector files installed into $PostgresRoot"

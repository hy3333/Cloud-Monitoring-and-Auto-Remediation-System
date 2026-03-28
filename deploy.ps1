param(
    [string]$StackName = "cloud-monitoring-stack",
    [string]$Region = "ap-south-2",
    [string]$FrontendPath = "frontend"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Cloud Monitoring Deploy Script ===" -ForegroundColor Cyan

if (!(Test-Path "samconfig.toml")) {
    throw "samconfig.toml not found in current directory."
}

if (!(Test-Path $FrontendPath)) {
    throw "Frontend folder not found: $FrontendPath"
}

Write-Host "`n[1/3] Building SAM application..." -ForegroundColor Yellow
sam build
if ($LASTEXITCODE -ne 0) {
    throw "sam build failed"
}

Write-Host "`n[2/3] Deploying SAM stack using existing samconfig.toml..." -ForegroundColor Yellow
sam deploy
if ($LASTEXITCODE -ne 0) {
    throw "sam deploy failed"
}

Write-Host "`n[3/3] Resolving frontend bucket output and syncing frontend files..." -ForegroundColor Yellow
$bucketName = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --region $Region `
    --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketNameOutput'].OutputValue" `
    --output text

if ([string]::IsNullOrWhiteSpace($bucketName) -or $bucketName -eq "None") {
    throw "Could not resolve FrontendBucketNameOutput from stack '$StackName' in region '$Region'. Check template outputs and samconfig parameters."
}

Write-Host "Resolved frontend bucket: $bucketName" -ForegroundColor Green

aws s3 sync $FrontendPath "s3://$bucketName/" --delete
if ($LASTEXITCODE -ne 0) {
    throw "aws s3 sync failed"
}

Write-Host ""
Write-Host "Deployment complete." -ForegroundColor Green
Write-Host "Next required step:" -ForegroundColor Cyan
Write-Host "- Trigger ASG Instance Refresh OR terminate the current ASG instance once" -ForegroundColor Cyan
Write-Host "- New instance will run User Data and pull latest frontend from S3" -ForegroundColor Cyan

# MemOS CLI Helper Script to push memory into MemOS from Terminal / PowerShell / Ollama Desktop logs
param (
    [Parameter(Mandatory=$true)]
    [string]$Content,
    [string]$Source = "terminal_cli",
    [string]$ServerUrl = "http://localhost:8000/api/v1/ollama/share-memory"
)

$body = @{
    content = $Content
    source = $Source
    tags = @("cli", "ollama_desktop")
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $ServerUrl -Method Post -Body $body -ContentType "application/json"
    Write-Host "✅ Memory successfully indexed into MemOS! (Memory ID: $($response.memory_id))" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to connect to MemOS server at $ServerUrl. Make sure MemOS backend is running." -ForegroundColor Red
}

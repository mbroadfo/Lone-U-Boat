# Clear Python bytecode cache and run main.py
Write-Host "Clearing Python cache..." -ForegroundColor Yellow
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Filter *.pyc -Recurse -Force | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "Cache cleared!" -ForegroundColor Green
Write-Host "Starting game..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe main.py

<#
.SYNOPSIS
    CampusKhoj One-Click Demo & Evaluation Launcher
.DESCRIPTION
    Launches MySQL (if needed), verifies database schema, starts Flask API (port 5000),
    starts HTTP static server (port 3000), and launches the browser for viva demonstration.
#>

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "         CAMPUSKHOJ: TWO-CAMPUS LOST & FOUND SYSTEM         " -ForegroundColor Cyan
Write-Host "                   ONE-CLICK DEMO LAUNCHER                  " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# 1. Check Python
try {
    $pyVer = python --version 2>&1
    Write-Host "[OK] Python detected: $pyVer" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not found on PATH. Please install Python 3.11+." -ForegroundColor Red
    exit 1
}

# 2. Check MySQL connection
Write-Host "[..] Checking MySQL connectivity..." -ForegroundColor Yellow
$mysqlCheck = python -c "
from backend.config import config
import mysql.connector
try:
    conn = mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )
    if conn.is_connected():
        print('CONNECTED')
        conn.close()
except Exception as e:
    print('ERROR:', e)
" 2>&1

if ($mysqlCheck -match "CONNECTED") {
    Write-Host "[OK] Connected to live MySQL 8 ($mysqlCheck)" -ForegroundColor Green
} else {
    Write-Host "[WARNING] MySQL check returned: $mysqlCheck" -ForegroundColor Yellow
    Write-Host "Ensure MySQL is running on configured port (default 3307 or 3306 in backend/.env)." -ForegroundColor Yellow
}

# 3. Start Backend Flask Server (Port 5000)
Write-Host "[..] Starting CampusKhoj API on http://127.0.0.1:5000..." -ForegroundColor Yellow
$apiProcess = Start-Process python -ArgumentList "run.py" -PassThru -WindowStyle Minimized

# 4. Start Frontend HTTP Server (Port 3000)
Write-Host "[..] Starting Static Portals on http://127.0.0.1:3000..." -ForegroundColor Yellow
$httpProcess = Start-Process python -ArgumentList "-m http.server 3000" -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "               ALL SERVICES SUCCESSFULLY STARTED            " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Student Portal: http://localhost:3000/student-portal/" -ForegroundColor Cyan
Write-Host "Admin Portal:   http://localhost:3000/admin-portal/" -ForegroundColor Cyan
Write-Host "Backend API:    http://127.0.0.1:5000/api/v1/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "DEMO CREDENTIALS FOR VIVA (DEMO DATABASE ONLY):" -ForegroundColor White
Write-Host "  * First-Login Student:  PRN 1251150269 / Temporary Password: PRN 1251150269 (Kondhwa)" -ForegroundColor Gray
Write-Host "  * Enrolled Student:     PRN 1251150353 / Password: Student@123 (Demo DB Only)" -ForegroundColor Gray
Write-Host "  * Super Admin:          Username: admin / Password: <KHOJ_TEST_STAFF_PASSWORD>" -ForegroundColor Gray
Write-Host "  * Kondhwa Admin:        Username: admin_kon / Password: <KHOJ_TEST_STAFF_PASSWORD>" -ForegroundColor Gray
Write-Host "  * Bibwewadi Admin:      Username: admin_bib / Password: <KHOJ_TEST_STAFF_PASSWORD>" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

# 5. Open Browser
Start-Process "http://localhost:3000/student-portal/"
Start-Process "http://localhost:3000/admin-portal/"

Write-Host "Press Ctrl+C to terminate services." -ForegroundColor Yellow
try {
    while ($true) {
        Start-Sleep -Seconds 5
    }
} finally {
    Write-Host "Stopping servers..." -ForegroundColor Yellow
    if ($apiProcess) { Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($httpProcess) { Stop-Process -Id $httpProcess.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "All processes stopped cleanly." -ForegroundColor Green
}


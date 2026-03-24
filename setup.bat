@echo off
:: =============================================================================
::   AegisLoop GRC — One-Click Deployment Script (Windows)
::   Version: 2.0.0
::   Usage:  Right-click → "Run as Administrator"  OR  double-click setup.bat
:: =============================================================================

setlocal EnableExtensions EnableDelayedExpansion
title AegisLoop GRC — Enterprise Setup

:: ── Colors via ANSI (requires Windows 10 1903+ / Windows Terminal) ───────────
reg query "HKCU\Console" /v VirtualTerminalLevel >nul 2>&1
if errorlevel 1 (
    reg add "HKCU\Console" /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1
)

set "BLUE=[34m"
set "GREEN=[32m"
set "YELLOW=[33m"
set "CYAN=[36m"
set "RED=[31m"
set "WHITE=[97m"
set "BOLD=[1m"
set "RESET=[0m"
set "DIM=[2m"

cls
echo.
echo %BLUE%%BOLD%  +===========================================================+
echo  ^|                                                           ^|
echo  ^|          AegisLoop GRC — Enterprise Compliance           ^|
echo  ^|          HIPAA  .  SOC 2  .  NIST  .  ISO 27001         ^|
echo  ^|                                                           ^|
echo  +===========================================================+%RESET%
echo.
echo   %DIM%Setup Script v2.0.0 for Windows%RESET%
echo.

:: ── Step 1: Check Prerequisites ──────────────────────────────────────────────
echo   %WHITE%%BOLD%^>  Checking Prerequisites%RESET%
echo   %DIM%------------------------------------------------------%RESET%

:: Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo   %RED%[ERROR]%RESET% Docker is not installed or not in PATH.
    echo.
    echo         Install Docker Desktop from:
    echo         https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)
for /f "tokens=3" %%v in ('docker --version 2^>nul') do set DOCKER_VER=%%v
echo   %GREEN%[OK]%RESET%    Docker found ^(!DOCKER_VER:~0,-1!^)

:: Check Docker daemon
docker info >nul 2>&1
if errorlevel 1 (
    echo   %RED%[ERROR]%RESET% Docker Desktop is not running.
    echo          Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)
echo   %GREEN%[OK]%RESET%    Docker daemon is running

:: Check Docker Compose (v2 preferred)
docker compose version >nul 2>&1
if errorlevel 1 (
    docker-compose --version >nul 2>&1
    if errorlevel 1 (
        echo   %RED%[ERROR]%RESET% Docker Compose is not available.
        echo          Install from: https://docs.docker.com/compose/install/
        pause
        exit /b 1
    )
    set COMPOSE_CMD=docker-compose
    echo   %GREEN%[OK]%RESET%    Docker Compose ^(standalone^) found
    echo   %YELLOW%[WARN]%RESET%  Consider upgrading to Docker Compose v2.
) else (
    set COMPOSE_CMD=docker compose
    echo   %GREEN%[OK]%RESET%    Docker Compose v2 found
)

echo.

:: ── Step 2: Interactive Configuration ────────────────────────────────────────
echo   %WHITE%%BOLD%^>  Platform Configuration%RESET%
echo   %DIM%------------------------------------------------------%RESET%
echo.
echo   %DIM%Configure your AegisLoop GRC installation below.
echo   Press ENTER to accept the default value shown in brackets.%RESET%
echo.

:: Admin Email
set "ADMIN_EMAIL=admin@aegisloop.io"
set /p "ADMIN_EMAIL=    Admin Email [default: admin@aegisloop.io]: "
if "!ADMIN_EMAIL!"=="" set "ADMIN_EMAIL=admin@aegisloop.io"

:: Admin Password
echo.
echo   %YELLOW%  Note: You will be prompted to change this password on first login.%RESET%
set "ADMIN_DEFAULT_PASSWORD=AegisLoop2026!"
set /p "ADMIN_DEFAULT_PASSWORD=    Admin Password [default: AegisLoop2026!]: "
if "!ADMIN_DEFAULT_PASSWORD!"=="" set "ADMIN_DEFAULT_PASSWORD=AegisLoop2026!"

:: JWT Secret — generate a pseudo-random value using PowerShell
echo.
echo   %CYAN%  Generating JWT secret key...%RESET%
for /f "delims=" %%s in ('powershell -NoProfile -Command "[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(36)) -replace '[/+=]',''" 2^>nul') do set "AUTO_JWT=%%s"
if "!AUTO_JWT!"=="" set "AUTO_JWT=aegis-enterprise-secret-CHANGE-ME-NOW"
set "JWT_SECRET_KEY=!AUTO_JWT!"
set /p "JWT_SECRET_KEY=    JWT Secret Key [auto-generated, press ENTER]: "
if "!JWT_SECRET_KEY!"=="" set "JWT_SECRET_KEY=!AUTO_JWT!"

:: LLM Model
echo.
echo   %DIM%    LLM Model Selection:%RESET%
echo   %DIM%      [1] qwen3-coder-next:cloud  ^(default, cloud-based^)%RESET%
echo   %DIM%      [2] ollama/codellama         ^(local Ollama server^)%RESET%
echo   %DIM%      [3] Enter a custom model name%RESET%
echo.
set LLM_CHOICE=1
set /p "LLM_CHOICE=    LLM Model choice [1/2/3, default: 1]: "
if "!LLM_CHOICE!"=="2" (
    set "LLM_MODEL=ollama/codellama"
) else if "!LLM_CHOICE!"=="3" (
    set /p "LLM_MODEL=    Custom model name: "
) else (
    set "LLM_MODEL=qwen3-coder-next:cloud"
)
echo   %GREEN%[OK]%RESET%    LLM Model: !LLM_MODEL!

echo.
set "OLLAMA_API_KEY="
set /p "OLLAMA_API_KEY=    LLM API Key (if required, else press ENTER to skip): "

:: ── Step 3: Generate .env File ───────────────────────────────────────────────
echo.
echo   %WHITE%%BOLD%^>  Writing Configuration%RESET%
echo   %DIM%------------------------------------------------------%RESET%

set "ENV_FILE=.env"

(
    echo # =========================================================================
    echo # AegisLoop GRC — Runtime Configuration
    echo # Generated by setup.bat
    echo # SECURITY: Do not commit this file to version control.
    echo # =========================================================================
    echo.
    echo # Admin Account
    echo ADMIN_EMAIL=!ADMIN_EMAIL!
    echo ADMIN_DEFAULT_PASSWORD=!ADMIN_DEFAULT_PASSWORD!
    echo.
    echo # JWT Authentication
    echo JWT_SECRET_KEY=!JWT_SECRET_KEY!
    echo JWT_EXPIRE_MINUTES=480
    echo.
    echo # LLM Integration
    echo OLLAMA_API_KEY=!OLLAMA_API_KEY!
    echo LLM_MODEL=!LLM_MODEL!
    echo.
    echo # Database
    echo DATABASE_URL=sqlite:///./ralph_loop.db
    echo.
    echo # OWASP ZAP
    echo ZAP_API_KEY=aegis-zap-internal
    echo.
    echo # CORS
    echo ALLOWED_ORIGINS=http://localhost:3000
) > "!ENV_FILE!"

echo   %GREEN%[OK]%RESET%    .env configuration file written

:: ── Step 4: Build & Launch ────────────────────────────────────────────────────
echo.
echo   %WHITE%%BOLD%^>  Building ^& Launching AegisLoop GRC%RESET%
echo   %DIM%------------------------------------------------------%RESET%
echo.
echo   %DIM%  Building Docker images and starting containers...%RESET%
echo   %DIM%  This may take 3-8 minutes on first run. Please wait.%RESET%
echo.

%COMPOSE_CMD% down --remove-orphans 2>nul
%COMPOSE_CMD% up -d --build

if errorlevel 1 (
    echo.
    echo   %RED%[ERROR]%RESET% Docker Compose failed to start. Check the output above for errors.
    echo          Common fixes:
    echo          - Ensure Docker Desktop has enough memory ^(^>= 4GB recommended^)
    echo          - Run: %COMPOSE_CMD% logs
    pause
    exit /b 1
)

:: ── Step 5: Health Check Wait ─────────────────────────────────────────────────
echo.
echo   %WHITE%%BOLD%^>  Waiting for Services to Become Ready%RESET%
echo   %DIM%------------------------------------------------------%RESET%
echo.

set /a "WAITED=0"
set "API_HEALTHY=false"

:HEALTH_LOOP
if !WAITED! GEQ 120 goto HEALTH_DONE
curl -sf "http://localhost:8000/health" >nul 2>&1
if not errorlevel 1 (
    set "API_HEALTHY=true"
    goto HEALTH_DONE
)
echo   %DIM%  Waiting for API service... ^(!WAITED!s^)%RESET%
timeout /t 5 /nobreak >nul
set /a "WAITED=!WAITED!+5"
goto HEALTH_LOOP

:HEALTH_DONE
if "!API_HEALTHY!"=="true" (
    echo   %GREEN%[OK]%RESET%    API service is healthy
) else (
    echo   %YELLOW%[WARN]%RESET%  API health check timed out. The app may still be loading.
    echo          Check logs with: %COMPOSE_CMD% logs api
)

:: ── Step 6: Success Banner ─────────────────────────────────────────────────────
echo.
echo   %GREEN%%BOLD%+===========================================================+
echo  ^|                                                           ^|
echo  ^|     SUCCESS — AegisLoop GRC is Ready!                    ^|
echo  ^|                                                           ^|
echo  +===========================================================+%RESET%
echo.
echo   %WHITE%%BOLD%  Access the Platform%RESET%
echo.
echo   %CYAN%    Dashboard:   %RESET% http://localhost:3000
echo   %CYAN%    API Docs:    %RESET% http://localhost:8000/docs
echo.
echo   %WHITE%%BOLD%  Login Credentials%RESET%
echo.
echo   %CYAN%    Email:      %RESET% !ADMIN_EMAIL!
echo   %CYAN%    Password:   %RESET% !ADMIN_DEFAULT_PASSWORD!
echo.
echo   %YELLOW%    ^> You will be required to change your password on first login.%RESET%
echo.
echo   %WHITE%%BOLD%  Useful Commands%RESET%
echo.
echo   %DIM%    View logs:       %COMPOSE_CMD% logs -f%RESET%
echo   %DIM%    Stop platform:   %COMPOSE_CMD% down%RESET%
echo   %DIM%    Restart:         %COMPOSE_CMD% restart%RESET%
echo   %DIM%    Apply branding:  edit theme.json, then %COMPOSE_CMD% restart frontend%RESET%
echo.
echo   %DIM%    Full documentation: COMMERCIAL_QUICK_START.md%RESET%
echo.

:: Open browser automatically
echo   %CYAN%  Opening dashboard in your default browser...%RESET%
timeout /t 3 /nobreak >nul
start "" "http://localhost:3000"

echo.
pause
endlocal

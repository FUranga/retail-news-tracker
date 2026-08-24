@echo off
echo Retail Wire — actualizando datos...
set REPO="C:\Users\Francisco.Uranga\OneDrive - William Reed Ltd\Documents\proyectos claude\news tracker"
set GIT="C:\Users\Francisco.Uranga\AppData\Local\GitHubDesktop\app-3.6.4\resources\app\git\cmd\git.exe"

%GIT% -C %REPO% pull
if %errorlevel% neq 0 (
    echo [WARN] git pull fallo — abriendo Claude Code igual con datos existentes
)

cd /d %REPO%
claude

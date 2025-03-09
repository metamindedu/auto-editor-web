@echo off
setlocal EnableDelayedExpansion
echo Auto-Editor Streamlit App Launcher
echo ===============================
echo.

:: Define virtual environment path
set VENV_DIR=venv

:: Check Python installation
set PYTHON_INSTALLED=0
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    for /f "tokens=*" %%i in ('python -c "import sys; print(sys.version.split()[0])"') do set PYTHON_VERSION=%%i
    echo Found Python version !PYTHON_VERSION!
    set PYTHON_INSTALLED=1
    
    :: Check Python version (we need at least 3.8)
    for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
        set MAJOR=%%a
        set MINOR=%%b
    )
    
    if !MAJOR! LSS 3 (
        echo WARNING: Python version !PYTHON_VERSION! is too old.
        set PYTHON_INSTALLED=0
    ) else if !MAJOR! EQU 3 if !MINOR! LSS 8 (
        echo WARNING: Python version !PYTHON_VERSION! is too old.
        set PYTHON_INSTALLED=0
    )
)

if !PYTHON_INSTALLED! EQU 0 (
    echo Python 3.8+ not found. Installing Python 3.10.11...
    
    :: Create temp directory for downloads
    if not exist "temp" mkdir temp
    cd temp
    
    :: Download Python installer
    echo Downloading Python 3.10.11 installer...
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe' -OutFile 'python-3.10.11-amd64.exe'}"
    
    if not exist "python-3.10.11-amd64.exe" (
        echo ERROR: Failed to download Python installer.
        cd ..
        pause
        exit /b 1
    )
    
    :: Install Python with necessary options
    echo Installing Python 3.10.11...
    start /wait python-3.10.11-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    :: Clean up installer
    del python-3.10.11-amd64.exe
    cd ..
    
    :: Refresh environment variables to include new Python
    echo Refreshing environment variables...
    call :RefreshEnv
    
    :: Verify Python installation
    where python >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Python installation failed or Python is not in PATH.
        echo Please install Python 3.10.11 manually and ensure it's added to your PATH.
        pause
        exit /b 1
    )
    
    echo Python 3.10.11 installed successfully.
)

:: Check for and create virtual environment if not exists
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Creating virtual environment in %VENV_DIR%...
    python -m venv %VENV_DIR%
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to create virtual environment.
        echo Make sure the venv module is available.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo Activating virtual environment...
call %VENV_DIR%\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo Virtual environment activated.

:: Check if we need to install dependencies
if not exist "setup_done.txt" (
    echo First-time setup: Installing required packages in virtual environment...
    
    echo - Upgrading pip...
    python -m pip install --upgrade pip
    if %ERRORLEVEL% neq 0 (
        echo WARNING: Failed to upgrade pip, continuing with existing version.
    )
    
    echo - Installing Streamlit...
    python -m pip install streamlit
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install Streamlit.
        pause
        exit /b 1
    )
    
    echo - Installing NumPy...
    python -m pip install numpy
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install NumPy.
        pause
        exit /b 1
    )
    
    echo - Installing PyAV...
    python -m pip install av
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install PyAV.
        pause
        exit /b 1
    )
    
    echo - Installing FFmpeg-python...
    python -m pip install ffmpeg-python
    if %ERRORLEVEL% neq 0 (
        echo WARNING: Failed to install ffmpeg-python, some functionality might not work.
    )
    
    :: Check for Auto-Editor
    if not exist auto-editor (
        echo Auto-Editor source not found.
        echo Downloading Auto-Editor...
        
        :: Try to use git if available
        where git >nul 2>nul
        if %ERRORLEVEL% equ 0 (
            git clone https://github.com/WyattBlue/auto-editor.git
            if %ERRORLEVEL% neq 0 (
                echo ERROR: Failed to download Auto-Editor with git.
                echo Please download Auto-Editor manually from:
                echo https://github.com/WyattBlue/auto-editor
                pause
                exit /b 1
            )
        ) else (
            echo Git is not available. Downloading Auto-Editor zip file...
            powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/WyattBlue/auto-editor/archive/refs/heads/master.zip' -OutFile 'auto-editor.zip'}"
            if %ERRORLEVEL% neq 0 (
                echo ERROR: Failed to download Auto-Editor zip file.
                echo Please download Auto-Editor manually from:
                echo https://github.com/WyattBlue/auto-editor
                pause
                exit /b 1
            )
            
            echo Extracting Auto-Editor...
            powershell -Command "& {Expand-Archive -Path 'auto-editor.zip' -DestinationPath '.\'}"
            if %ERRORLEVEL% neq 0 (
                echo ERROR: Failed to extract Auto-Editor.
                pause
                exit /b 1
            )
            
            echo Renaming directory...
            move auto-editor-master auto-editor
            del auto-editor.zip
        )
    )
    
    :: Check for sample video and download if needed
    if not exist "example.mp4" (
        if exist "auto-editor\example.mp4" (
            echo Copying sample video from Auto-Editor...
            copy "auto-editor\example.mp4" "example.mp4"
        ) else if exist "auto-editor\resources\testsrc.mp4" (
            echo Copying sample video from Auto-Editor resources...
            copy "auto-editor\resources\testsrc.mp4" "example.mp4"
        ) else (
            echo Downloading sample video...
            powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/WyattBlue/auto-editor/raw/master/resources/testsrc.mp4' -OutFile 'example.mp4'}"
            if %ERRORLEVEL% neq 0 (
                echo WARNING: Failed to download sample video.
                echo You will need to provide your own video files.
            ) else (
                echo Sample video downloaded successfully.
            )
        )
    )
    
    echo Installing Auto-Editor into virtual environment...
    python -m pip install -e ./auto-editor
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install Auto-Editor.
        echo Please make sure the auto-editor directory exists and is complete.
        pause
        exit /b 1
    )
    
    echo Setup completed successfully.
    echo 1 > setup_done.txt
)

:: Run the Streamlit app
echo Starting Auto-Editor Streamlit app...
echo.
echo The app will open in your web browser automatically.
echo When you're done, close this window to stop the app.
echo.
:: start http://localhost:8501
python -m streamlit run app.py

:: Deactivate venv when done
echo Deactivating virtual environment...
call %VENV_DIR%\Scripts\deactivate.bat

pause

:: Function to refresh environment variables without restarting the script
:RefreshEnv
echo @echo off>"%TEMP%\_env.cmd"
call :_GetRegEnv HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment >> "%TEMP%\_env.cmd"
call :_GetRegEnv HKCU\Environment >> "%TEMP%\_env.cmd"
for /f "delims=" %%A in ('type "%TEMP%\_env.cmd"') do set %%A
del /f /q "%TEMP%\_env.cmd"
goto :eof

:_GetRegEnv RegPath
for /f "tokens=1,2*" %%A in ('reg query "%~1" /ve 2^>nul') do (
    if "%%A"=="REG_EXPAND_SZ" echo %%C
    if "%%A"=="REG_SZ" echo %%C
)
for /f "tokens=1,2*" %%A in ('reg query "%~1" 2^>nul') do (
    if "%%A"=="REG_EXPAND_SZ" echo %%C
    if "%%A"=="REG_SZ" echo %%C
)
goto :eof
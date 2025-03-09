@echo off
echo Auto-Editor Streamlit App Launcher
echo ===============================
echo.

:: Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python and try again.
    pause
    exit /b 1
)

:: Check if we need to install dependencies
if not exist "setup_done.txt" (
    echo First-time setup: Installing required packages...
    
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
    
    echo Installing Auto-Editor...
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

pause
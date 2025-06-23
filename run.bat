@echo off
title Project Runner

echo ===================================================
echo  Starting the Bumble Setup and Run Script
echo ===================================================
echo.

:: STEP 1: PULL LATEST CHANGES FROM GIT
echo [STEP 1/4] Pulling latest changes from Git...
git pull
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: 'git pull' failed.
    echo Please check for local changes you need to commit or stash.
    echo Also, ensure Git is installed and you have an internet connection.
    goto :error
)
echo Git pull successful.
echo.

:: STEP 2: CHECK FOR AND CREATE A VIRTUAL ENVIRONMENT
echo [STEP 2/4] Checking for Python virtual environment...
if not exist venv\ (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo.
        echo ERROR: Failed to create the virtual environment.
        echo Please make sure Python is installed and added to your system PATH.
        goto :error
    )
    echo Virtual environment created successfully.
) else (
    echo Virtual environment found.
)
echo.

:: STEP 3: INSTALL/UPDATE PACKAGES
echo [STEP 3/4] Activating environment and installing packages...
call venv\Scripts\activate
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: 'pip install' failed.
    echo Please check your requirements.txt file and internet connection.
    goto :error
)
echo Packages installed successfully.
echo.

:: STEP 4: RUN THE MAIN APPLICATION
echo [STEP 4/4] Running the main application (cli.py)...
echo ===================================================
echo.
python cli.py
echo.
echo ===================================================
echo Application has finished.
goto :end

:error
echo.
echo !!! An error occurred. The script cannot continue. !!!
echo Please take a screenshot of this window and send it to support.

:end
echo.
echo Press any key to close this window...
pause >nul

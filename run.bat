@echo off
title Project Runner - Final Version

:: =================================================================
:: == SCRIPT SAFETY HARNESS                                       ==
:: == This structure makes it nearly impossible for the window    ==
:: == to close on its own.                                        ==
:: =================================================================

:: 1. The script's first and only main command is to "call" the logic below.
call :run_all_logic

:: 2. After the logic finishes (or fails and exits), execution ALWAYS returns here.
::    This is the safety net. It will pause the script UNCONDITIONALLY.
echo.
echo #######################################################################
echo ###                                                               ###
echo ###   The script has finished or was stopped by an error.         ###
echo ###   THE WINDOW IS NOW PAUSED AND WILL NOT CLOSE AUTOMATICALLY.  ###
echo ###   Review all messages above to see what happened.             ###
echo ###                                                               ###
echo #######################################################################
echo.
pause
exit


:: =================================================================
:: == ALL SETUP AND RUN LOGIC IS CONTAINED IN THIS SUBROUTINE     ==
:: =================================================================
:run_all_logic

echo ===================================================
echo  Starting the Project Setup and Run Script
echo ===================================================
echo.

:: STEP 1: PULL LATEST CHANGES FROM GIT
echo [STEP 1/4] Pulling latest changes from Git...
git pull
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: 'git pull' failed.
    goto :eof
)
echo Git pull successful.
echo.

:: STEP 2: ACTIVATE VENV & INSTALL PACKAGES
echo [STEP 2/4] Activating environment and installing packages...
if not exist venv\Scripts\activate (
    echo ERROR: Virtual environment not found. Please delete the 'venv' folder and run again.
    goto :eof
)
call venv\Scripts\activate
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: 'pip install' failed.
    goto :eof
)
echo Python packages installed successfully.
echo.

:: ==========================================================
:: == STEP 3: RUN 'APPIUM SETUP' - THE USER'S WAY
:: ==========================================================
echo [STEP 3/4] Running Appium dependency setup...
echo This will check for and install necessary drivers and dependencies.

:: First, a quick check that the appium command exists at all.
where appium >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo.
    echo FATAL ERROR: The 'appium' command was not found on your system.
    echo Please ensure Node.js is installed, then run 'npm install -g appium'.
    goto :eof
)

echo About to run the 'appium setup' command. This may take a few minutes...
echo.

:: We use 'call' because appium is a .cmd file. 'call' runs it and waits
:: for it to finish, which is safer and prevents crashes.
call appium setup

:: We check the result of the 'appium setup' command.
if %ERRORLEVEL% neq 0 (
    echo.
    echo WARNING: The 'appium setup' command finished with an error code.
    echo However, we will attempt to continue anyway.
    echo Please review any error messages from Appium above.
    echo.
) else (
    echo Appium setup completed successfully.
    echo.
)


:: STEP 4: RUN THE MAIN APPLICATION
echo [STEP 4/4] Running the main application (cli.py)...
echo ===================================================
echo.
python cli.py

echo.
echo ===================================================
echo Application has finished successfully.

:: This command tells the script to exit this logic block and return
:: to the "safety harness" section above.
goto :eof

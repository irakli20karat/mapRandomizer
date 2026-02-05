@echo off
setlocal enabledelayedexpansion

echo ========================================
echo SkyRandomizer Build Script
echo ========================================
echo.

REM Set paths
set PYTHON27=C:\Python27\python.exe
set MOD_FOLDER=mod
set BUILD_FOLDER=build
set OUTPUT_NAME=sbRandomizer.wotmod

REM Check if mod folder exists
if not exist "%MOD_FOLDER%" (
    echo ERROR: mod folder not found!
    echo Please create a 'mod' folder with your Python files
    echo Example structure: mod\scripts\client\gui\mods\SkyRandomizer.py
    pause
    exit /b 1
)

REM Check if Python 2.7 exists
if not exist "%PYTHON27%" (
    echo WARNING: Python 2.7 not found at %PYTHON27%
    echo Skipping compilation, copying .py files as-is
    set SKIP_COMPILE=1
) else (
    echo Python 2.7 found: %PYTHON27%
    set SKIP_COMPILE=0
)
echo.

REM Clean build folder
if exist "%BUILD_FOLDER%" (
    echo Cleaning old build folder...
    rmdir /s /q "%BUILD_FOLDER%" 2>nul
)

REM Create build folder
echo Creating build folder...
mkdir "%BUILD_FOLDER%" 2>nul
if not exist "%BUILD_FOLDER%" (
    echo ERROR: Failed to create build folder
    pause
    exit /b 1
)

REM Copy mod folder structure to build
echo Copying mod folder to build...
xcopy "%MOD_FOLDER%\*" "%BUILD_FOLDER%\" /E /I /Y /Q
if errorlevel 1 (
    echo ERROR: Failed to copy files
    pause
    exit /b 1
)
echo Copy complete.
echo.

REM Compile .py files if Python is available
if "%SKIP_COMPILE%"=="0" (
    echo Compiling Python files to .pyc...
    for /r "%BUILD_FOLDER%" %%f in (*.py) do (
        echo Compiling: %%~nxf
        "%PYTHON27%" -m py_compile "%%f"
        if errorlevel 1 (
            echo WARNING: Failed to compile %%f
        )
    )
    
    echo.
    echo Removing .py source files...
    for /r "%BUILD_FOLDER%" %%f in (*.py) do (
        del "%%f" 2>nul
    )
    echo Compilation complete.
) else (
    echo Skipping compilation - .py files will be included
)
echo.

REM Create the .wotmod
echo Creating %OUTPUT_NAME%...
if exist "%OUTPUT_NAME%" del "%OUTPUT_NAME%" 2>nul

REM Check for 7-Zip
set SEVENZIP=C:\Program Files\7-Zip\7z.exe
if not exist "%SEVENZIP%" set SEVENZIP=C:\Program Files (x86)\7-Zip\7z.exe
if not exist "%SEVENZIP%" set SEVENZIP=7z.exe

where /q 7z.exe
if errorlevel 1 (
    if not exist "%SEVENZIP%" (
        echo ERROR: 7-Zip not found!
        echo Please install 7-Zip from https://www.7-zip.org/
        echo Or make sure 7z.exe is in your PATH
        pause
        exit /b 1
    )
)

echo Using 7-Zip to create archive (store mode, no compression)...
pushd "%BUILD_FOLDER%"
"%SEVENZIP%" a -tzip -mx0 "..\%OUTPUT_NAME%" * -r
set BUILD_ERROR=!ERRORLEVEL!
popd

if %BUILD_ERROR% NEQ 0 (
    echo ERROR: 7-Zip failed with error code %BUILD_ERROR%
    pause
    exit /b 1
)

if not exist "%OUTPUT_NAME%" (
    echo ERROR: %OUTPUT_NAME% was not created!
    echo.
    echo Build folder contents:
    dir "%BUILD_FOLDER%" /s /b
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build SUCCESSFUL!
echo Output: %CD%\%OUTPUT_NAME%
echo Size: 
for %%A in ("%OUTPUT_NAME%") do echo %%~zA bytes
echo ========================================
echo.

REM Optional: Clean up build folder
set /p CLEANUP="Clean up build folder? (Y/N): "
if /i "%CLEANUP%"=="Y" (
    echo Cleaning build folder...
    rmdir /s /q "%BUILD_FOLDER%" 2>nul
    echo Build folder removed.
) else (
    echo Build folder kept for inspection.
)

echo.
echo Done!
pause
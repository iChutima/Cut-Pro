@echo off
echo ========================================
echo Cut Pro - Mini Tool Build Script
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python first
    pause
    exit /b 1
)

:: Check if required files exist
if not exist "auto.py" (
    echo ERROR: auto.py not found
    pause
    exit /b 1
)

if not exist "icon.ico" (
    echo WARNING: icon.ico not found - executable will use default icon
)

if not exist "icon.png" (
    echo WARNING: icon.png not found - dialog icons may not work properly
)

echo Installing required packages...
echo.

:: Install required packages
pip install pillow customtkinter opencv-python pyinstaller requests

if %errorlevel% neq 0 (
    echo ERROR: Failed to install packages
    pause
    exit /b 1
)

echo.
echo Building executable with icons...
echo.

:: Clean any previous builds
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del "*.spec"

:: Create the executable with PyInstaller
pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "CutPro" ^
    --icon="%~dp0icon.ico" ^
    --add-data "%~dp0icon.png;." ^
    --add-data "%~dp0icon.ico;." ^
    --hidden-import="PIL._tkinter_finder" ^
    --hidden-import="tkinter" ^
    --hidden-import="tkinter.filedialog" ^
    --hidden-import="tkinter.messagebox" ^
    --hidden-import="customtkinter" ^
    --hidden-import="PIL" ^
    --hidden-import="PIL.Image" ^
    --hidden-import="cv2" ^
    --hidden-import="inspect" ^
    --hidden-import="pkg_resources" ^
    --hidden-import="importlib_metadata" ^
    --hidden-import="threading" ^
    --hidden-import="subprocess" ^
    --hidden-import="pathlib" ^
    --hidden-import="json" ^
    --hidden-import="requests" ^
    --hidden-import="uuid" ^
    --hidden-import="datetime" ^
    --hidden-import="hashlib" ^
    --hidden-import="urllib3" ^
    --hidden-import="urllib3.util" ^
    --hidden-import="urllib3.util.retry" ^
    --hidden-import="requests.adapters" ^
    --hidden-import="ssl" ^
    --collect-submodules="urllib3" ^
    --hidden-import="certifi" ^
    --hidden-import="charset_normalizer" ^
    --hidden-import="idna" ^
    --hidden-import="zipfile" ^
    --hidden-import="shutil" ^
    --hidden-import="platform" ^
    --collect-submodules="customtkinter" ^
    --collect-submodules="PIL" ^
    --exclude-module="pytest" ^
    --exclude-module="unittest" ^
    --exclude-module="test" ^
    --exclude-module="pdb" ^
    --exclude-module="doctest" ^
    --clean ^
    auto.py

if %errorlevel% neq 0 (
    echo ERROR: Build failed
    echo Cleaning up temporary files...
    if exist "build" rmdir /s /q "build"
    if exist "CutPro.spec" del "CutPro.spec"
    pause
    exit /b 1
)

echo.
echo Cleaning up temporary files...
echo.

:: Remove build folder
if exist "build" (
    rmdir /s /q "build"
    echo - Removed build folder
)

:: Remove spec file
if exist "CutPro.spec" (
    del "CutPro.spec"
    echo - Removed CutPro.spec file
)

:: Remove __pycache__ folders if they exist
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
        echo - Removed %%d
    )
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\CutPro.exe
echo.
echo Features included:
echo - License activation system with server validation
echo - Standalone FFmpeg auto-download (no manual install needed)
echo - Main window taskbar icon (icon.ico)
echo - Dialog window icons (icon.png + icon.ico)
echo - Custom blue title bars with icons
echo - All video processing tools
echo - Quality Enhancer (1080p, 2K, 4K)
echo - Blur Background (9:16 ↔ 16:9 Box Blur conversion)
echo - GPU Acceleration: NVIDIA/AMD/Intel hardware acceleration support
echo - Automatic CPU fallback for maximum compatibility
echo - Quality options: 1080p, 2K, 4K (Box Blur only)
echo - No console window
echo.
echo You can now distribute the CutPro.exe file as a standalone executable.
echo FFmpeg will be downloaded automatically on first use.
echo.
echo IMPORTANT: System Requirements:
echo - Requires internet connection for license activation
echo - Requires internet connection for FFmpeg auto-download (first use only)
echo - License server: https://license-server-pro.vercel.app/
echo - Product ID: cutpro-mini
echo - Users must activate license before using any features
echo.

:: FFmpeg auto-download info
echo NOTE: FFmpeg Auto-Download Feature
echo The executable will automatically download FFmpeg on first use.
echo No manual FFmpeg installation is required.
echo Users will see a download dialog when first processing videos.
echo.

echo Build process completed!
echo.
echo Icon Features:
echo ✅ Taskbar icon (development and compiled)
echo ✅ Window title bar icon
echo ✅ All dialog custom headers with icons
echo ✅ No console window in compiled version
echo.
echo License System Features:
echo ✅ Server-based license validation
echo ✅ License key persistence (remembered after first use)
echo ✅ Manual activation required each session
echo ✅ All features disabled until license activated
echo ✅ Auto-closing success dialogs
echo ✅ Remaining days display
echo.
echo FFmpeg Auto-Download Features:
echo ✅ Automatic FFmpeg download on first use
echo ✅ Professional download dialog with progress bar
echo ✅ Cross-platform support (Windows/Mac/Linux)
echo ✅ No manual installation required
echo ✅ Standalone executable distribution
echo ✅ Local FFmpeg storage in app directory
echo.
pause
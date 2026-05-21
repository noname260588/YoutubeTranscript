@echo off
echo ============================================
echo   YouTube Knowledge Clipper - Build Script
echo ============================================
echo.

echo [1/3] Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements.
    pause
    exit /b 1
)

echo.
echo [2/3] Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller.
    pause
    exit /b 1
)

echo.
echo.
echo [3/4] Checking FFmpeg bundle files...
if not exist "ffmpeg" mkdir "ffmpeg"

if not exist "ffmpeg\ffmpeg.exe" (
    echo ffmpeg\ffmpeg.exe not found. Trying to copy from system PATH...
    for /f "delims=" %%F in ('where ffmpeg 2^>nul') do (
        copy "%%F" "ffmpeg\ffmpeg.exe" >nul
        goto ffmpeg_ready
    )
    echo ERROR: ffmpeg.exe not found.
    echo Put ffmpeg.exe in the ffmpeg\ folder or install FFmpeg in system PATH.
    pause
    exit /b 1
)

:ffmpeg_ready
if not exist "ffmpeg\ffprobe.exe" (
    echo ffmpeg\ffprobe.exe not found. Trying to copy from system PATH...
    for /f "delims=" %%F in ('where ffprobe 2^>nul') do (
        copy "%%F" "ffmpeg\ffprobe.exe" >nul
        goto ffprobe_ready
    )
    echo WARNING: ffprobe.exe not found. Continuing with ffmpeg.exe only.
)

:ffprobe_ready
echo FFmpeg files ready for bundling.

echo.
echo [4/4] Building executable (onefile)...
pyinstaller --noconsole ^
    --noconfirm ^
    --onefile ^
    --name YouTubeKnowledgeClipper ^
    --icon icon.ico ^
    --add-data "icon.ico;." ^
    --add-data "author.png;." ^
    --add-data "help.png;." ^
    --add-data "prompt_templates.json;." ^
    --add-data "ffmpeg;ffmpeg" ^
    --hidden-import customtkinter ^
    --hidden-import faster_whisper ^
    --hidden-import youtube_transcript_api ^
    --hidden-import yt_dlp ^
    --hidden-import pyperclip ^
    --hidden-import keyboard ^
    --hidden-import PIL.ImageTk ^
    app.py

if errorlevel 1 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build complete!
echo   Output: dist\YouTubeKnowledgeClipper.exe
echo ============================================
echo.
echo FFmpeg is bundled into the onefile executable.
echo Runtime folders will be created next to the executable when needed:
echo   - models\   (Whisper models)
echo   - downloads\ (temporary audio/video files)
echo   - exports\   (exported transcripts)
echo.
pause

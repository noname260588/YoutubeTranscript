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
echo [3/3] Building executable (portable folder)...
pyinstaller --noconsole ^
    --name YouTubeKnowledgeClipper ^
    --add-data "ffmpeg;ffmpeg" ^
    --hidden-import customtkinter ^
    --hidden-import faster_whisper ^
    --hidden-import youtube_transcript_api ^
    --hidden-import yt_dlp ^
    --hidden-import pyperclip ^
    app.py

if errorlevel 1 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build complete!
echo   Output: dist\YouTubeKnowledgeClipper\
echo ============================================
echo.
echo Remember to copy these folders to dist\YouTubeKnowledgeClipper\:
echo   - ffmpeg\   (with ffmpeg.exe)
echo   - models\   (Whisper models will be downloaded here)
echo   - downloads\ (temporary audio files)
echo   - exports\   (exported transcripts)
echo.
pause

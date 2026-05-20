# YouTube Knowledge Clipper — Desktop App Spec

## 1. Vai trò của AI Builder

Bạn là **Senior Python Developer + Software Architect**.

Hãy build một ứng dụng desktop Windows dạng portable `.exe` tên là:

```txt
YouTube Knowledge Clipper
```

Ứng dụng dùng để:

1. Lấy transcript có sẵn từ video YouTube.
2. Nếu video không có transcript, tự động tải audio và dùng speech-to-text offline để tạo transcript.
3. Xuất kết quả thành `.txt`, `.md`, hoặc `.srt`.
4. Tối ưu cho workflow học tập, ghi chú, PKM và Obsidian.

---

## 2. Mục tiêu sản phẩm

Build một desktop app đơn giản, dễ dùng, chạy trên Windows.

Người dùng chỉ cần:

```txt
Paste YouTube URL
→ bấm Get Transcript
→ app tự lấy transcript hoặc tự chạy speech-to-text
→ copy hoặc export file
```

Ứng dụng cần hoạt động theo 2 mode:

```txt
Mode 1: YouTube Transcript Mode
Lấy transcript/caption có sẵn từ YouTube.

Mode 2: Speech-to-Text Mode
Nếu không có transcript, tải audio bằng yt-dlp rồi chuyển audio thành text bằng faster-whisper.
```

---

## 3. Tech Stack bắt buộc

Sử dụng:

```txt
Python 3.10+
CustomTkinter
youtube-transcript-api
yt-dlp
faster-whisper
pyperclip
PyInstaller
ffmpeg
```

File `requirements.txt`:

```txt
customtkinter
youtube-transcript-api
yt-dlp
faster-whisper
pyperclip
```

---

## 4. Kiến trúc thư mục

Tạo project theo cấu trúc:

```txt
youtube-knowledge-clipper/
├─ app.py
├─ transcript_service.py
├─ audio_service.py
├─ whisper_service.py
├─ export_service.py
├─ utils.py
├─ requirements.txt
├─ build.bat
├─ README.md
├─ ffmpeg/
│  └─ ffmpeg.exe
├─ models/
│  └─ .gitkeep
├─ downloads/
│  └─ .gitkeep
└─ exports/
   └─ .gitkeep
```

Ý nghĩa:

```txt
app.py
Main desktop UI bằng CustomTkinter.

transcript_service.py
Lấy transcript có sẵn từ YouTube bằng youtube-transcript-api.

audio_service.py
Tải audio từ YouTube bằng yt-dlp.

whisper_service.py
Chạy speech-to-text bằng faster-whisper.

export_service.py
Xuất kết quả ra .txt, .md, .srt.

utils.py
Hàm phụ: parse video ID, format timestamp, sanitize filename.

build.bat
Lệnh build thành .exe bằng PyInstaller.
```

---

## 5. Core Workflow

### 5.1 Luồng chính

```txt
User paste YouTube URL
↓
App validate URL
↓
Extract video ID
↓
Try fetch transcript from YouTube
↓
If transcript exists:
    show transcript
    allow copy/export
Else:
    ask user to run Speech-to-Text
↓
Download audio with yt-dlp
↓
Transcribe audio with faster-whisper
↓
Show transcript with timestamps
↓
Export .txt / .md / .srt
```

---

## 6. UI Requirements

Thiết kế UI đơn giản, hiện đại, gọn.

Dùng CustomTkinter.

### 6.1 Main Window

Kích thước mặc định:

```txt
900 x 650
```

Theme:

```txt
Dark mode
Rounded cards
Clean layout
```

### 6.2 Thành phần UI

Gồm các phần:

```txt
Title:
YouTube Knowledge Clipper

Input:
- YouTube URL textbox
- Button: Get Transcript

Options:
- Language dropdown: Auto, vi, en, ja, zh
- Mode dropdown:
  - Auto
  - Transcript Only
  - Speech-to-Text Only

Speech-to-Text Settings:
- Whisper model:
  - tiny
  - base
  - small
  - medium
- Device:
  - CPU
- Compute type:
  - int8

Output:
- Large textbox hiển thị transcript

Buttons:
- Copy
- Save TXT
- Save Markdown
- Save SRT
- Clear
```

### 6.3 Trạng thái xử lý

Cần có status label:

```txt
Ready
Checking transcript...
Transcript found.
No transcript found. Running speech-to-text...
Downloading audio...
Transcribing audio...
Done.
Error: ...
```

Không để app bị đơ UI khi xử lý lâu.  
Dùng `threading` để chạy tác vụ nặng ở background thread.

---

## 7. Transcript Service

File: `transcript_service.py`

Chức năng:

```python
get_youtube_transcript(video_url: str, language: str = "auto") -> list[dict]
```

Output format:

```python
[
    {
        "start": 0.0,
        "duration": 3.2,
        "text": "Hello world"
    }
]
```

Yêu cầu:

1. Parse video ID từ URL.
2. Thử lấy transcript theo language user chọn.
3. Nếu language là `auto`, ưu tiên:
   - `vi`
   - `en`
   - transcript auto-generated nếu có
4. Nếu không lấy được, raise custom exception:

```python
TranscriptNotFoundError
```

---

## 8. Audio Service

File: `audio_service.py`

Chức năng:

```python
download_audio(video_url: str, output_dir: str = "downloads") -> str
```

Output:

```txt
Path tới file audio .mp3
```

Yêu cầu:

1. Dùng `yt-dlp`.
2. Download best audio.
3. Convert sang `.mp3` bằng ffmpeg.
4. Lưu vào thư mục `downloads`.
5. Sanitize filename để tránh lỗi Windows path.
6. Return full path file audio.

Cấu hình yt-dlp mẫu:

```python
ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(title)s.%(ext)s",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
}
```

Nếu dùng ffmpeg local trong thư mục `ffmpeg/`, cần cấu hình path tương ứng.

---

## 9. Whisper Speech-to-Text Service

File: `whisper_service.py`

Chức năng:

```python
transcribe_audio(
    audio_path: str,
    model_size: str = "small",
    language: str | None = None
) -> list[dict]
```

Output:

```python
[
    {
        "start": 0.0,
        "end": 3.2,
        "text": "Xin chào mọi người"
    }
]
```

Cấu hình mặc định:

```python
from faster_whisper import WhisperModel

model = WhisperModel(
    model_size,
    device="cpu",
    compute_type="int8"
)
```

Transcribe:

```python
segments, info = model.transcribe(
    audio_path,
    language=language,
    beam_size=5,
    vad_filter=True
)
```

Yêu cầu:

1. Hỗ trợ model:
   - tiny
   - base
   - small
   - medium
2. Default model: `small`
3. Default device: `cpu`
4. Default compute type: `int8`
5. Có progress/status callback nếu có thể.
6. Không crash app nếu model chưa có hoặc download model lỗi.
7. Hiển thị lỗi thân thiện.

---

## 10. Export Service

File: `export_service.py`

Cần support 3 định dạng:

```txt
.txt
.md
.srt
```

### 10.1 TXT Format

```txt
YouTube Transcript
Source: {{url}}
Language: {{language}}

[00:00:01] Nội dung...
[00:00:05] Nội dung...
```

### 10.2 Markdown Format

```md
# {{video_title}}

Source: {{url}}
Date: {{date}}
Language: {{language}}
Mode: {{mode}}

## Transcript

[00:00:01] Nội dung...
[00:00:05] Nội dung...
```

### 10.3 SRT Format

```srt
1
00:00:01,000 --> 00:00:05,000
Nội dung...

2
00:00:05,000 --> 00:00:09,000
Nội dung tiếp theo...
```

Cần có hàm:

```python
export_txt(segments, output_path, metadata)
export_markdown(segments, output_path, metadata)
export_srt(segments, output_path, metadata)
```

---

## 11. Utility Functions

File: `utils.py`

Cần có:

```python
extract_video_id(url: str) -> str
format_timestamp(seconds: float) -> str
format_srt_timestamp(seconds: float) -> str
sanitize_filename(name: str) -> str
ensure_dirs() -> None
```

`extract_video_id` cần support các dạng URL:

```txt
https://www.youtube.com/watch?v=VIDEO_ID
https://youtu.be/VIDEO_ID
https://www.youtube.com/shorts/VIDEO_ID
https://m.youtube.com/watch?v=VIDEO_ID
```

---

## 12. Error Handling

App cần xử lý lỗi thân thiện.

Các lỗi phổ biến:

```txt
Invalid YouTube URL
Transcript not found
Audio download failed
FFmpeg not found
Whisper model load failed
Speech-to-text failed
Permission denied when saving file
Network error
```

Không để app crash.

Hiển thị message box hoặc status label rõ ràng.

---

## 13. Build EXE

Tạo file `build.bat`:

```bat
@echo off
echo Installing requirements...
pip install -r requirements.txt

echo Building executable...
pyinstaller --onefile --noconsole --name YouTubeKnowledgeClipper app.py

echo Done.
pause
```

Nếu dùng folder portable, có thể dùng:

```bat
pyinstaller --noconsole --name YouTubeKnowledgeClipper app.py
```

Khuyến nghị:

```txt
Không nên nhét model Whisper vào one-file exe.
Nên build dạng portable folder để dễ update model và ffmpeg.
```

Folder release nên là:

```txt
YouTubeKnowledgeClipper/
├─ YouTubeKnowledgeClipper.exe
├─ ffmpeg/
│  └─ ffmpeg.exe
├─ models/
├─ downloads/
└─ exports/
```

---

## 14. README Requirements

File `README.md` cần có:

```md
# YouTube Knowledge Clipper

## Features

- Get YouTube transcript
- Fallback to offline speech-to-text
- Export TXT, Markdown, SRT
- Copy transcript to clipboard
- Obsidian-friendly Markdown export

## Install for development

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

## Build EXE

```bat
build.bat
```

## Notes

- Transcript mode depends on available YouTube captions.
- Speech-to-text mode requires downloading audio.
- FFmpeg is required for audio conversion.
- Whisper model may be downloaded on first run.
```
```

---

## 15. MVP Acceptance Criteria

App được xem là hoàn thành MVP khi:

```txt
[ ] User paste YouTube URL
[ ] App lấy được transcript nếu video có caption
[ ] App fallback sang speech-to-text nếu không có transcript
[ ] App tải audio bằng yt-dlp thành công
[ ] App transcribe audio bằng faster-whisper
[ ] App hiển thị transcript trong textbox
[ ] User copy transcript được
[ ] User save .txt được
[ ] User save .md được
[ ] User save .srt được
[ ] App không bị freeze khi xử lý video dài
[ ] App có status progress rõ ràng
[ ] Có build.bat để đóng gói .exe
```

---

## 16. Nice-to-have Features

Nếu còn thời gian, thêm:

```txt
[ ] Auto get video title
[ ] Auto detect language
[ ] Remove repeated lines
[ ] Clean filler words
[ ] Split transcript by timestamp
[ ] Split transcript by paragraph
[ ] Save directly to Obsidian Inbox folder
[ ] Remember last export folder
[ ] Dark/light theme toggle
[ ] Drag and drop local audio file for transcription
```

---

## 17. Prompt Build Full App

Copy prompt này đưa cho AI coding tool:

```txt
You are a Senior Python Developer and Software Architect.

Build a Windows desktop app named "YouTube Knowledge Clipper".

The app must be written in Python 3.10+ using CustomTkinter.

Main goal:
The user pastes a YouTube URL, clicks "Get Transcript", and the app tries to fetch the available YouTube transcript first. If no transcript is available, the app downloads the video's audio using yt-dlp and transcribes it offline using faster-whisper.

Required features:
1. Input YouTube URL.
2. Extract video ID from standard YouTube URLs, youtu.be URLs, Shorts URLs, and mobile YouTube URLs.
3. Try fetching transcript using youtube-transcript-api.
4. If transcript is not found, fallback to speech-to-text mode.
5. Download audio using yt-dlp.
6. Convert audio to mp3 using ffmpeg.
7. Transcribe audio using faster-whisper.
8. Show transcript in a large textbox.
9. Allow user to copy transcript.
10. Allow export as TXT.
11. Allow export as Markdown.
12. Allow export as SRT.
13. Use background threading for long-running tasks so the UI does not freeze.
14. Show status messages for each processing step.
15. Handle errors gracefully with user-friendly messages.
16. Include requirements.txt.
17. Include build.bat for PyInstaller.
18. Include README.md.

Project structure:
- app.py
- transcript_service.py
- audio_service.py
- whisper_service.py
- export_service.py
- utils.py
- requirements.txt
- build.bat
- README.md
- downloads/
- exports/
- ffmpeg/
- models/

Default settings:
- Whisper model: small
- Device: CPU
- Compute type: int8
- Language options: Auto, vi, en, ja, zh

UI requirements:
Use a clean dark modern interface.
Window size: 900x650.
Include:
- App title
- YouTube URL input
- Get Transcript button
- Mode dropdown: Auto, Transcript Only, Speech-to-Text Only
- Language dropdown: Auto, vi, en, ja, zh
- Whisper model dropdown: tiny, base, small, medium
- Transcript output textbox
- Buttons: Copy, Save TXT, Save Markdown, Save SRT, Clear
- Status label

Export formats:
TXT should include source URL, language, and timestamped transcript.
Markdown should be Obsidian-friendly with title, source, date, language, mode, and transcript.
SRT should follow valid SRT timestamp format.

Important:
Do not crash when transcript is unavailable.
Do not freeze UI during download/transcription.
Do not hardcode user-specific paths.
Use pathlib where possible.
Make the code clean, modular, and production-ready for an MVP.
```

---

## 18. Gợi ý phát triển bản Pro

Sau MVP, có thể nâng cấp thành:

```txt
YouTube → Transcript → Summary → Obsidian Note
```

Thêm các tính năng:

```txt
- Auto summarize
- Extract key ideas
- Extract quotes
- Create study notes
- Create flashcards
- Create mindmap outline
- Export to Markdown vault
```

Obsidian Markdown nâng cao:

```md
# {{video_title}}

> Source: {{url}}
> Date: {{date}}
> Language: {{language}}

## 1. Summary

## 2. Key Ideas

## 3. Important Quotes

## 4. Full Transcript

## 5. My Notes
```

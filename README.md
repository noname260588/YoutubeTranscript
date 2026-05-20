# 🎬 YouTube Knowledge Clipper

> Ứng dụng desktop Windows giúp trích xuất transcript từ video YouTube — phục vụ học tập, ghi chú và PKM (Personal Knowledge Management).

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows)

---

## ✨ Features

| Tính năng | Mô tả |
|-----------|-------|
| 🎯 **YouTube Transcript** | Lấy transcript/caption có sẵn từ YouTube |
| 🎤 **Speech-to-Text Offline** | Tự động tải audio + chuyển thành text bằng faster-whisper |
| ⬇️ **Download Video** | Tải video chất lượng cao (best video+audio) từ YouTube |
| ⏱️ **Timestamps Toggle** | Bật/tắt hiển thị timestamp trong transcript |
| 📋 **Copy to Clipboard** | Copy transcript chỉ với 1 click |
| 💾 **Export TXT** | Xuất plain text với timestamp |
| 📝 **Export Markdown** | Xuất Obsidian-friendly markdown với metadata |
| 🎬 **Export SRT** | Xuất phụ đề chuẩn SRT |
| 🌐 **Multi-language** | Hỗ trợ Vietnamese, English, Japanese, Chinese |
| 🌙 **Dark Mode UI** | Giao diện dark hiện đại với CustomTkinter |
| ⚡ **Non-blocking** | Xử lý nặng chạy background, UI không bị đơ |

---

## 🚀 Quick Start

### 1. Clone dự án

```bash
git clone <repo-url>
cd YoutubeTranscript
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 3. Chạy ứng dụng

```bash
python app.py
```

### 4. Sử dụng

```
Paste YouTube URL → Bấm "Get Transcript" → Copy hoặc Export file
```

---

## 📦 Tech Stack

| Thư viện | Vai trò |
|----------|---------|
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Desktop UI framework (dark theme) |
| [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) | Lấy transcript có sẵn từ YouTube |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Download audio từ YouTube |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Speech-to-text offline (Whisper CTranslate2) |
| [pyperclip](https://github.com/asweigart/pyperclip) | Copy text vào clipboard |
| [FFmpeg](https://ffmpeg.org/) | Convert audio sang MP3 |

---

## 📁 Project Structure

```
YoutubeTranscript/
├── app.py                   # Main desktop UI (CustomTkinter)
├── transcript_service.py    # Lấy transcript từ YouTube API
├── audio_service.py         # Download audio bằng yt-dlp
├── whisper_service.py       # Speech-to-text bằng faster-whisper
├── export_service.py        # Xuất file TXT, Markdown, SRT
├── utils.py                 # Utility: parse URL, format timestamp, sanitize filename
├── requirements.txt         # Python dependencies
├── build.bat                # Build portable EXE bằng PyInstaller
├── README.md                # Documentation
├── .gitignore               # Git ignore rules
├── ffmpeg/                  # FFmpeg executable (tự đặt vào)
│   └── ffmpeg.exe
├── models/                  # Whisper models (auto-download lần đầu)
├── downloads/               # Audio files tạm (tự tạo khi chạy)
└── exports/                 # Transcript files đã export
```

---

## ⚙️ Cấu hình

### Mode hoạt động

| Mode | Mô tả |
|------|-------|
| **Auto** | Thử lấy transcript trước, nếu không có thì fallback sang STT |
| **Transcript Only** | Chỉ lấy transcript có sẵn từ YouTube |
| **Speech-to-Text Only** | Bỏ qua transcript, luôn tải audio + chạy Whisper |

### Whisper Models

| Model | Kích thước | Tốc độ | Độ chính xác |
|-------|-----------|--------|-------------|
| `tiny` | ~75 MB | ⚡ Rất nhanh | Thấp |
| `base` | ~140 MB | ⚡ Nhanh | Trung bình |
| `small` | ~460 MB | 🔄 Vừa | Tốt |
| `medium` | ~1.5 GB | 🐌 Chậm | Rất tốt |

> **Mặc định**: `small` / CPU / int8 — cân bằng giữa tốc độ và chất lượng.

---

## 📤 Export Formats

### TXT
```
YouTube Transcript
Source: https://youtube.com/watch?v=...
Language: vi

[00:00:01] Nội dung dòng 1...
[00:00:05] Nội dung dòng 2...
```

### Markdown (Obsidian-friendly)
```markdown
# Video Title

> Source: https://youtube.com/watch?v=...
> Date: 2026-05-20
> Language: vi
> Mode: YouTube Transcript

## Transcript

[00:00:01] Nội dung...

## My Notes

<!-- Add your notes here -->
```

### SRT
```
1
00:00:01,000 --> 00:00:05,000
Nội dung dòng 1...

2
00:00:05,000 --> 00:00:09,000
Nội dung dòng 2...
```

---

## 🔨 Build EXE

Tạo portable `.exe` cho Windows:

```bat
build.bat
```

Output: `dist/YouTubeKnowledgeClipper/`

> ⚠️ **Lưu ý**: Sau khi build, cần copy thêm thư mục `ffmpeg/`, `models/`, `downloads/`, `exports/` vào thư mục output.

---

## ⚠️ Lưu ý quan trọng

- **FFmpeg**: Cần đặt `ffmpeg.exe` vào thư mục `ffmpeg/` cạnh `app.py` (hoặc cài vào system PATH) để sử dụng Speech-to-Text mode.
- **Whisper Model**: Lần chạy đầu tiên ở mode STT sẽ tự động download model từ Hugging Face (~460MB cho `small`). Cần có internet.
- **Transcript mode**: Phụ thuộc vào việc video có caption/phụ đề hay không. Nhiều video không có sẵn transcript.
- **Hiệu suất STT**: Chạy trên CPU nên video dài có thể mất vài phút. Model `tiny` nhanh nhất nếu cần tốc độ.

---

## 📋 Supported YouTube URL Formats

```
https://www.youtube.com/watch?v=VIDEO_ID
https://youtu.be/VIDEO_ID
https://www.youtube.com/shorts/VIDEO_ID
https://m.youtube.com/watch?v=VIDEO_ID
```

---

## 🛣️ Roadmap

- [ ] Auto detect video title
- [ ] Remove repeated/filler lines
- [ ] Split transcript by paragraph
- [ ] Save directly to Obsidian vault
- [ ] Remember last export folder
- [ ] Dark/Light theme toggle
- [ ] Drag & drop local audio file
- [ ] Auto summarize with AI
- [ ] Extract key ideas & quotes

---

## 📄 License

MIT License — Free to use, modify, and distribute.

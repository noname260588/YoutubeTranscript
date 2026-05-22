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
| ⬇️ **Download Video/Audio** | Tải video MP4 hoặc audio M4A từ YouTube |
| 📊 **Download Progress** | Hiển thị phần trăm, tốc độ và ETA khi `yt-dlp` cung cấp |
| ⛔ **Cancel Download** | Hủy tác vụ tải video/audio đang chạy |
| ⏱️ **Timestamps Toggle** | Bật/tắt hiển thị timestamp trong transcript |
| 📋 **Copy to Clipboard** | Copy transcript chỉ với 1 click |
| ⌨️ **Global Hotkey** | Bôi đen link YouTube và nhấn `Ctrl + Shift + C` để đưa link vào app |
| 🍪 **Browser Cookies** | Tự retry bằng cookies Edge/Chrome/Firefox khi YouTube yêu cầu đăng nhập |
| 💾 **Export TXT** | Xuất plain text với timestamp |
| 📝 **Export Markdown** | Xuất Obsidian-friendly Markdown với frontmatter và clean mode |
| 🗂️ **Obsidian Direct Export** | Lưu Markdown thẳng vào vault/subfolder đã cấu hình |
| ⚙️ **Persistent Settings** | Nhớ folder export, language, mode, Whisper model và timestamp toggle |
| 🔎 **YouTube Metadata** | Lấy title, channel, description, thumbnail, tags, categories bằng yt-dlp không download |
| 🧩 **Prompt Template Generator** | Tạo prompt offline từ transcript và metadata để copy sang AI/chat tool |
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
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Download video/audio từ YouTube |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Speech-to-text offline (Whisper CTranslate2) |
| [pyperclip](https://github.com/asweigart/pyperclip) | Copy text vào clipboard |
| [keyboard](https://github.com/boppreh/keyboard) | Global hotkey `Ctrl + Shift + C` |
| [FFmpeg](https://ffmpeg.org/) | Convert audio và merge video/audio |

---

## 📁 Project Structure

```
YoutubeTranscript/
├── app.py                   # Main desktop UI (CustomTkinter)
├── transcript_service.py    # Lấy transcript từ YouTube API
├── audio_service.py         # Download audio bằng yt-dlp
├── video_service.py         # Download video MP4 hoặc audio M4A bằng yt-dlp
├── whisper_service.py       # Speech-to-text bằng faster-whisper
├── export_service.py        # Xuất file TXT, Markdown, SRT
├── prompt_templates.json    # Prompt templates offline
├── services/                # Metadata và prompt template services
│   ├── prompt_template_service.py
│   └── youtube_metadata_service.py
├── utils.py                 # Utility: parse URL, format timestamp, sanitize filename
├── requirements.txt         # Python dependencies
├── build.bat                # Build portable EXE bằng PyInstaller
├── README.md                # Documentation
├── .gitignore               # Git ignore rules
├── icon.ico                 # App icon
├── author.png               # Ảnh About dialog
├── help.png                 # Ảnh hướng dẫn sử dụng
├── ffmpeg/                  # FFmpeg binaries used by PyInstaller bundling
│   ├── ffmpeg.exe
│   └── ffprobe.exe
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

### Download options

| Tuỳ chọn | Giá trị |
|---------|---------|
| **Format** | `Video (MP4)`, `Audio (M4A)` |
| **Video Quality** | `480p` mặc định để tải nhanh; có thể chọn `Best`, `1080p`, `720p`, `480p` |
| **Browser Cookies** | `Auto`, `None`, `Edge`, `Chrome`, `Firefox`, `Brave`, `Vivaldi`, `Opera` |

> **Browser Cookies = Auto**: App tải thường trước. Nếu YouTube trả lỗi `Sign in to confirm you’re not a bot`, app sẽ thử lại bằng cookies từ các trình duyệt có cookie database trên máy. Cách này yêu cầu bạn đã đăng nhập YouTube trong trình duyệt đó.

### Whisper Models

| Model | Kích thước | Tốc độ | Độ chính xác |
|-------|-----------|--------|-------------|
| `tiny` | ~75 MB | ⚡ Rất nhanh | Thấp |
| `base` | ~140 MB | ⚡ Nhanh | Trung bình |
| `small` | ~460 MB | 🔄 Vừa | Tốt |
| `medium` | ~1.5 GB | 🐌 Chậm | Rất tốt |

> **Mặc định**: `small` / CPU / int8 — cân bằng giữa tốc độ và chất lượng.

---

## 🧩 Prompt Template Generator

Prompt Template Generator hoạt động hoàn toàn offline, không gọi AI API. App chỉ dựng sẵn prompt từ transcript hiện tại và metadata YouTube để bạn copy sang công cụ AI/chat khác.

Luồng sử dụng:

1. Lấy transcript như bình thường.
2. Chọn prompt type: Key Ideas, Lessons Learned, Obsidian Note, Facebook Post, Viral Caption, Slide Deck, Flashcards, Action Checklist hoặc Product Ideas.
3. Chọn transcript mode cho prompt: Clean Transcript, Raw Transcript hoặc Transcript with timestamps.
4. Bấm **Generate Prompt** để xem preview.
5. Bấm **Copy Prompt Only** nếu muốn giữ placeholder `{TRANSCRIPT}`.
6. Bấm **Copy Prompt + Transcript** nếu muốn chèn transcript hiện tại vào prompt.

Template có thể chỉnh trực tiếp trong `prompt_templates.json`. Các biến được hỗ trợ:

```text
{VIDEO_TITLE}
{VIDEO_URL}
{CHANNEL_NAME}
{DESCRIPTION}
{CHAPTERS}
{TRANSCRIPT}
```

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
---
type: youtube-note
title: "Video Title"
source: "https://youtube.com/watch?v=..."
language: "vi"
created: "2026-05-21"
mode: "Clean Transcript"
tags:
  - youtube
  - transcript
---

# Video Title

## Summary

## Key Ideas

## Quotes

## Transcript

[00:00:01] Nội dung transcript...

## My Notes
```

Markdown export hỗ trợ 3 mode trong Settings:

- **Raw Transcript**: giữ transcript gần nguyên bản.
- **Clean Transcript**: rule-based, chuẩn hóa whitespace, gộp segment ngắn, bỏ dòng lặp và chia đoạn dễ đọc.
- **Learning Notes**: template Obsidian với các heading học tập và transcript đã clean.

Markdown export có thể bật thêm trong Settings:

- **Include metadata**: thêm `## Video Info`.
- **Include video description**: thêm `## Description`.
- **Clean description**: chuẩn hóa whitespace/dòng trống trong description.
- **Extract chapters**: đọc timestamp trong description và thêm `## Chapters`.

### Obsidian Direct Export

Mở **Settings** để cấu hình:

- `Obsidian Vault Path`: vault hoặc folder Markdown đích.
- `Default subfolder`: mặc định `Resources/YouTube`.
- `Filename pattern`: mặc định `{date_compact}_{title}` để tạo file kiểu `20260521_video-title.md`.
- `Auto open file after export`: mở file Markdown sau khi lưu.

Nếu chưa cấu hình vault, khi bấm **Save MD** app sẽ hỏi folder và nhớ lại cho lần sau.

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

Output: `dist/YouTubeKnowledgeClipper/YouTubeKnowledgeClipper.exe`

> ⚠️ **Lưu ý**: Bản build dùng PyInstaller `--onedir` và nhúng `ffmpeg/ffmpeg.exe` cùng `ffmpeg/ffprobe.exe` vào thư mục. Trước khi build, cần có các binary này trong thư mục `ffmpeg/`; nếu thiếu, `build.bat` sẽ thử copy từ system PATH.

---

## 🍏 Hướng dẫn chạy trên macOS (Mac)

Bản build cho Mac được tạo tự động thông qua GitHub Actions và nén dưới dạng file `.zip`. Vì ứng dụng không được đăng ký (code-sign) bằng tài khoản Apple Developer trả phí, macOS sẽ bật cơ chế bảo vệ Gatekeeper trong lần mở đầu tiên.

### Cài đặt và Mở ứng dụng:
1. Tải file `YouTubeKnowledgeClipper-macOS.zip` từ mục **Artifacts** trong tab **Actions** trên GitHub.
2. Giải nén file zip, bạn sẽ nhận được ứng dụng `YouTubeKnowledgeClipperMac.app`.
3. Khi bạn click đúp để mở lần đầu, macOS sẽ hiện cảnh báo: *"YouTubeKnowledgeClipperMac" Not Opened*. Hãy nhấn **Done**.
4. Mở **System Settings** (Cài đặt hệ thống) > **Privacy & Security** (Quyền riêng tư & Bảo mật).
5. Cuộn xuống phần Security, bạn sẽ thấy thông báo ứng dụng bị chặn. Nhấn nút **Open Anyway** (Vẫn mở).
6. Bấm **Open** ở hộp thoại xác nhận tiếp theo. Các lần sau ứng dụng sẽ tự mở bình thường.

### Lưu ý cho Mac:
- **FFmpeg**: Bản Mac không nhúng sẵn thư viện `ffmpeg`. Nếu bạn muốn dùng tính năng tải Video/Audio hoặc dùng Speech-to-Text, bạn cần cài ffmpeg vào máy Mac bằng lệnh Terminal: `brew install ffmpeg`.
- **Phím tắt toàn cục**: Tính năng bôi đen và nhấn `Ctrl + Shift + C` tạm thời bị vô hiệu hóa trên macOS vì Apple yêu cầu cấp quyền Root/Trợ năng (Accessibility) rất phức tạp cho thư viện `keyboard`.

---

## ⚠️ Lưu ý quan trọng

- **FFmpeg**: Khi chạy từ source, app tìm `ffmpeg/ffmpeg.exe` cạnh `app.py` hoặc FFmpeg trong system PATH. Khi chạy bản đã build, FFmpeg được nhúng sẵn trong thư mục ứng dụng.
- **Whisper Model**: Lần chạy đầu tiên ở mode STT sẽ tự động download model từ Hugging Face (~460MB cho `small`). Cần có internet.
- **Transcript mode**: Phụ thuộc vào việc video có caption/phụ đề hay không. Nhiều video không có sẵn transcript.
- **Hiệu suất STT**: Chạy trên CPU nên video dài có thể mất vài phút. Model `tiny` nhanh nhất nếu cần tốc độ.
- **Global hotkey**: `Ctrl + Shift + C` dùng thư viện `keyboard`; trên một số máy Windows có thể cần quyền phù hợp để bắt phím toàn cục.
- **YouTube bot check**: Nếu gặp lỗi `Sign in to confirm you’re not a bot`, hãy đăng nhập YouTube trên Edge/Chrome/Firefox rồi để `Browser Cookies = Auto` hoặc chọn đúng trình duyệt đang đăng nhập.

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

- [x] Auto detect video title
- [x] Remove repeated/filler lines (rule-based Markdown clean mode)
- [x] Split transcript by paragraph (rule-based Markdown clean mode)
- [x] Save directly to Obsidian vault
- [x] Remember last export folder
- [x] Global Hotkey (`Ctrl + Shift + C`) to auto-fill URL
- [x] Offline Prompt Template Generator (Key ideas, Quotes, Summaries)
- [x] Extract YouTube metadata (Chapters, Description, Tags)
- [x] In-app Tutorial & About dialog with static image support
- [ ] Dark/Light theme toggle
- [ ] Drag & drop local audio file
- [ ] Auto summarize with local AI (without copy-pasting)

---

## 📄 License

MIT License — Free to use, modify, and distribute.

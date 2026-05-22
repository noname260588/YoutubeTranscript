# 🏗️ Kiến trúc Ứng dụng (Architecture)

Tài liệu này mô tả kiến trúc tổng thể của **YouTube Knowledge Clipper**, cách các module tương tác với nhau, và luồng xử lý dữ liệu từ UI xuống các dịch vụ ngầm (Background Services).

## 1. Cấu trúc Tổng thể (High-Level Architecture)

Ứng dụng được thiết kế theo mô hình **Monolithic UI với Modular Services**. Thay vì nhồi nhét toàn bộ logic vào file giao diện, các tác vụ nặng (Tải file, Chạy AI, Lấy Metadata) được tách riêng thành các file `*_service.py`.

Giao diện (`app.py`) chỉ đóng vai trò là "Người điều phối" (Controller), tiếp nhận tương tác từ người dùng và đẩy xuống các Service xử lý trong các luồng ngầm (Background Threads).

## 2. Các Module chính (Core Modules)

### A. Tầng Giao diện (Presentation Layer)
- **`app.py`**: Trái tim của giao diện, được xây dựng bằng `CustomTkinter`. 
  - Ứng dụng sử dụng kiến trúc **TabView** để chia rẽ các tính năng không liên quan nhằm bảo vệ UX:
    - **Tab "Video Đơn"**: Nhập 1 link YouTube, hiển thị Output ngay lập tức, lấy Prompt.
    - **Tab "Tải Playlist"**: Nhập link Playlist, quét hàng loạt video, tải ngầm Batch Processing và tự động tạo thư mục con.
  - Sử dụng hàng đợi Event Loop của Tkinter (`self.after`) để cập nhật giao diện từ các luồng ngầm (đảm bảo Thread-safe).

### B. Tầng Dịch vụ (Service Layer)
Nơi chứa toàn bộ Business Logic:
- **`transcript_service.py`**: Gọi API không chính thức của YouTube thông qua `youtube-transcript-api` để lấy phụ đề (nhanh, nhẹ, không tốn tài nguyên).
- **`audio_service.py` & `video_service.py`**: Sử dụng `yt-dlp` dể tải luồng Media. Tích hợp tính năng inject Browser Cookies để vượt qua xác thực bot của YouTube.
- **`whisper_service.py`**: Gói gọn thư viện AI `faster-whisper`. Module này chịu trách nhiệm tải Model từ HuggingFace trong lần chạy đầu tiên và biên dịch âm thanh thành văn bản hoàn toàn Offline bằng CPU.
- **`youtube_metadata_service.py`**: Lấy siêu dữ liệu (Title, Duration, Chapters) cực nhanh bằng `yt-dlp` ở chế độ `extract_flat=True` (đặc biệt hữu ích khi quét Playlist).
- **`export_service.py`**: Xử lý định dạng đầu ra. Định dạng Markdown có thể tự động nhúng Frontmatter (dành cho Obsidian), Chapters, Description và Metadata.
- **`prompt_template_service.py`**: Thay thế các biến động (Variables) trong Template JSON bằng dữ liệu thực tế.

## 3. Luồng Xử lý Dữ liệu (Data Flow)

### Kịch bản: Bấm nút "Lấy Transcript" (Video Đơn)
1. **User** bấm nút `⚡ Lấy Transcript`.
2. **UI (`app.py`)** khóa các nút bấm, hiện Progress Bar dạng vòng lặp (Indeterminate), sau đó khởi tạo một `threading.Thread`.
3. **Background Thread**:
   - Gọi `get_youtube_metadata()` để lấy Tên video.
   - Kiểm tra Chế độ (Mode). Nếu là "Auto":
     - Cố gắng gọi `get_youtube_transcript()`. Nếu thành công -> Trả về UI ngay.
     - Nếu YouTube chặn hoặc không có phụ đề -> Fallback sang STT.
   - Nếu Fallback STT:
     - Gọi `download_audio()` lưu file tạm vào `/downloads`.
     - Gọi `transcribe_audio()` từ `whisper_service.py`. Model AI phân tích file tạm sinh ra text.
4. **Kết thúc Thread**: Gọi `self.after(0, _on_success)` để đẩy chuỗi văn bản lên màn hình (Output Textbox), hiển thị số từ, thời gian chạy.

### Kịch bản: Tải Hàng loạt Playlist
1. **Quét (Scan)**: `get_playlist_info()` dùng `yt-dlp` quét phẳng (Flat) lấy danh sách Video ID siêu nhanh. Hiển thị UI Checkbox.
2. **Vòng lặp Batch**: UI tạo Thread mới lặp qua từng Video được Check.
   - Mỗi video đi qua chu trình: Tải Audio -> Chạy Whisper -> Export ra `.md` thẳng vào ổ cứng.
   - UI được cập nhật liên tục qua màn hình Log thay vì can thiệp vào Output Textbox.

## 4. Quản lý Trạng thái và Tài nguyên (State & Resource Management)
- **Tệp Cấu hình (`settings.json`)**: Lưu trữ thư mục xuất file, ngôn ngữ, Mode, Model.
- **Quản lý Thư mục Runtime**: Các thư mục `/downloads`, `/exports`, `/models` được tự động khởi tạo bằng `utils.ensure_dirs()`. Rác trong `/downloads` sẽ không được xóa tự động mà ghi đè lên file `temp_audio.m4a` để tránh phình dung lượng.
- **Đóng gói Cực đoan (Deployment)**: Thay vì dùng `--onefile` (làm chậm tốc độ khởi động do giải nén 200MB mỗi lần mở), ứng dụng được build dưới dạng `--onedir` (Giải nén sẵn). Tốc độ khởi động trên Windows hiện tại đạt dưới 1 giây. File `ffmpeg.exe` được đặt ngay cạnh mã nguồn để PyInstaller gói vào.

---
*Bản vẽ kiến trúc này được cập nhật theo phiên bản mới nhất hỗ trợ Playlist và Giao diện Đa Tab.*

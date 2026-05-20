"""
YouTube Knowledge Clipper — Main Application
Desktop app for extracting YouTube transcripts and speech-to-text.
Built with CustomTkinter for a modern dark UI.
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

import customtkinter as ctk
import keyboard
import pyperclip

from utils import (
    extract_video_id,
    ensure_dirs,
    get_base_dir,
    sanitize_filename,
    get_current_date,
    get_ffmpeg_path,
)
from transcript_service import get_youtube_transcript, TranscriptNotFoundError
from audio_service import download_audio, AudioDownloadError, get_video_info
from video_service import download_video, VideoDownloadError
from whisper_service import transcribe_audio, WhisperTranscriptionError
from export_service import (
    export_txt,
    export_markdown,
    export_srt,
    format_transcript_text,
)


# ─── App Constants ───────────────────────────────────────────────
APP_TITLE = "YouTube Knowledge Clipper"
APP_VERSION = "1.0.0"
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 720

LANGUAGES = ["Auto", "vi", "en", "ja", "zh"]
MODES = ["Auto", "Transcript Only", "Speech-to-Text Only"]
WHISPER_MODELS = ["tiny", "base", "small", "medium"]

# ─── Color Palette ───────────────────────────────────────────────
C_BG_DARK = "#0d1117"
C_BG_CARD = "#161b22"
C_BG_INPUT = "#1c2333"
C_BORDER = "#30363d"
C_ACCENT = "#58a6ff"
C_ACCENT_HOVER = "#79c0ff"
C_ACCENT_2 = "#3fb950"
C_TEXT = "#e6edf3"
C_TEXT_DIM = "#8b949e"
C_RED = "#f85149"
C_ORANGE = "#d29922"
C_PURPLE = "#bc8cff"


# ═════════════════════════════════════════════════════════════════
#  MAIN APP
# ═════════════════════════════════════════════════════════════════

class YouTubeKnowledgeClipperApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # ─── Window Setup ────────────────────────────────────────
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(800, 600)
        self.configure(fg_color=C_BG_DARK)

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - WINDOW_WIDTH) // 2
        y = (self.winfo_screenheight() - WINDOW_HEIGHT) // 2
        self.geometry(f"+{x}+{y}")

        # App icon
        try:
            icon_path = get_base_dir() / "icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        # ─── State ───────────────────────────────────────────────
        self.current_segments: list[dict] = []
        self.current_metadata: dict = {}
        self.is_processing = False

        # ─── Ensure Directories ──────────────────────────────────
        ensure_dirs()

        # ─── Set Appearance ──────────────────────────────────────
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # ─── Global Hotkey Setup ──────────────────────────────────
        try:
            keyboard.add_hotkey('ctrl+shift+c', self._on_global_hotkey)
        except Exception as e:
            print(f"Could not register global hotkey: {e}")

        # ─── Build UI ────────────────────────────────────────────
        self._build_ui()


    # ═════════════════════════════════════════════════════════════
    #  UI BUILDING
    # ═════════════════════════════════════════════════════════════

    def _build_ui(self):
        """Build the complete UI layout."""
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(3, weight=1)

        self._build_header(row=0)
        self._build_input_section(row=1)
        self._build_options_section(row=2)
        self._build_output_section(row=3)
        self._build_action_buttons(row=4)
        self._build_status_bar(row=5)

    def _build_header(self, row: int):
        """Header section."""
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        # Small corner app icon
        try:
            from PIL import Image
            icon_path = get_base_dir() / "icon.ico"
            if icon_path.exists():
                sheep_img = ctk.CTkImage(
                    light_image=Image.open(str(icon_path)),
                    size=(28, 28)
                )
                self.icon_label = ctk.CTkLabel(
                    header_frame,
                    text="",
                    image=sheep_img
                )
                self.icon_label.pack(side="left", padx=(0, 10))
        except Exception:
            pass

        self.title_label = ctk.CTkLabel(
            header_frame,
            text="YouTube Knowledge Clipper",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=C_TEXT,
        )
        self.title_label.pack(side="left")

        version_label = ctk.CTkLabel(
            header_frame,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color=C_TEXT_DIM,
            fg_color=C_BG_CARD,
            corner_radius=8,
            padx=8,
            pady=2,
        )
        version_label.pack(side="left", padx=(10, 0))

    def _build_input_section(self, row: int):
        """URL input + Get Transcript button."""
        self.input_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=C_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=C_BORDER,
        )
        self.input_card.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        self.input_card.columnconfigure(0, weight=1)

        url_label = ctk.CTkLabel(
            self.input_card,
            text="🔗 YouTube URL",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_TEXT_DIM,
        )
        url_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(12, 4))

        self.url_entry = ctk.CTkEntry(
            self.input_card,
            placeholder_text="Paste YouTube URL here... (Hoặc bôi đen link và bấm Ctrl + Shift + C)",
            font=ctk.CTkFont(size=13),
            height=42,
            fg_color=C_BG_INPUT,
            border_color=C_BORDER,
            text_color=C_TEXT,
            corner_radius=10,
        )
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=(16, 8), pady=(0, 4))
        self.url_entry.bind("<Return>", lambda e: self._on_get_transcript())
        
        hint_label = ctk.CTkLabel(
            self.input_card,
            text="💡 Mẹo: Bôi đen một link YouTube bất kỳ đâu (trên trình duyệt, tin nhắn...) và nhấn Ctrl + Shift + C để app tự động copy và xử lý!",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color=C_TEXT_DIM,
        )
        hint_label.grid(row=2, column=0, columnspan=3, sticky="w", padx=16, pady=(0, 10))

        self.get_btn = ctk.CTkButton(
            self.input_card,
            text="⚡ Get Transcript",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=42,
            width=150,
            fg_color=C_ACCENT,
            hover_color=C_ACCENT_HOVER,
            corner_radius=10,
            command=self._on_get_transcript,
        )
        self.get_btn.grid(row=1, column=1, sticky="e", padx=(0, 8), pady=(0, 4))

        self.download_video_btn = ctk.CTkButton(
            self.input_card,
            text="⬇️ Download",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=42,
            width=150,
            fg_color=C_PURPLE,
            hover_color=self._lighten_color(C_PURPLE),
            corner_radius=10,
            command=self._on_download_video,
        )
        self.download_video_btn.grid(row=1, column=2, sticky="e", padx=(0, 16), pady=(0, 4))

    def _build_options_section(self, row: int):
        """Options: Language, Mode, Whisper settings, Show timestamps toggle."""
        self.options_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=C_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=C_BORDER,
        )
        self.options_card.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        for i in range(5):
            self.options_card.columnconfigure(i, weight=1)

        # ── Row 0-1: Language
        self._make_option_label(self.options_card, "🌐 Language", 0, 0)
        self.language_var = ctk.StringVar(value="Auto")
        self.language_dropdown = ctk.CTkOptionMenu(
            self.options_card,
            variable=self.language_var,
            values=LANGUAGES,
            font=ctk.CTkFont(size=12),
            fg_color=C_BG_INPUT,
            button_color=C_BORDER,
            button_hover_color=C_ACCENT,
            dropdown_fg_color=C_BG_CARD,
            dropdown_hover_color=C_ACCENT,
            corner_radius=8,
            width=130,
        )
        self.language_dropdown.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        # ── Row 0-1: Mode
        self._make_option_label(self.options_card, "⚙️ Mode", 0, 1)
        self.mode_var = ctk.StringVar(value="Auto")
        self.mode_dropdown = ctk.CTkOptionMenu(
            self.options_card,
            variable=self.mode_var,
            values=MODES,
            font=ctk.CTkFont(size=12),
            fg_color=C_BG_INPUT,
            button_color=C_BORDER,
            button_hover_color=C_ACCENT,
            dropdown_fg_color=C_BG_CARD,
            dropdown_hover_color=C_ACCENT,
            corner_radius=8,
            width=180,
        )
        self.mode_dropdown.grid(row=1, column=1, padx=16, pady=(0, 12), sticky="w")

        # ── Row 0-1: Whisper Model
        self._make_option_label(self.options_card, "🤖 Whisper Model", 0, 2)
        self.whisper_model_var = ctk.StringVar(value="small")
        self.whisper_model_dropdown = ctk.CTkOptionMenu(
            self.options_card,
            variable=self.whisper_model_var,
            values=WHISPER_MODELS,
            font=ctk.CTkFont(size=12),
            fg_color=C_BG_INPUT,
            button_color=C_BORDER,
            button_hover_color=C_ACCENT,
            dropdown_fg_color=C_BG_CARD,
            dropdown_hover_color=C_ACCENT,
            corner_radius=8,
            width=120,
        )
        self.whisper_model_dropdown.grid(row=1, column=2, padx=16, pady=(0, 12), sticky="w")

        # ── Row 0-1: Device
        self._make_option_label(self.options_card, "💻 Device", 0, 3)
        self.device_label = ctk.CTkLabel(
            self.options_card,
            text="CPU • int8",
            font=ctk.CTkFont(size=12),
            text_color=C_TEXT_DIM,
            fg_color=C_BG_INPUT,
            corner_radius=8,
            padx=12,
            pady=4,
            width=100,
        )
        self.device_label.grid(row=1, column=3, padx=16, pady=(0, 12), sticky="w")

        # ── Row 0-1: Show Timestamps Toggle
        self._make_option_label(self.options_card, "⏱️ Timestamps", 0, 4)
        self.show_timestamps_var = ctk.BooleanVar(value=True)
        self.timestamps_switch = ctk.CTkSwitch(
            self.options_card,
            text="Show",
            font=ctk.CTkFont(size=12),
            variable=self.show_timestamps_var,
            onvalue=True,
            offvalue=False,
            fg_color=C_BORDER,
            progress_color=C_ACCENT,
            button_color=C_TEXT,
            button_hover_color=C_ACCENT_HOVER,
            command=self._on_toggle_timestamps,
        )
        self.timestamps_switch.grid(row=1, column=4, padx=16, pady=(0, 12), sticky="w")

        # ── Row 2-3: Download Format
        self._make_option_label(self.options_card, "📥 Download Format", 2, 0)
        self.download_format_var = ctk.StringVar(value="Video (MP4)")
        self.download_format_dropdown = ctk.CTkOptionMenu(
            self.options_card,
            variable=self.download_format_var,
            values=["Video (MP4)", "Audio (M4A)"],
            font=ctk.CTkFont(size=12),
            fg_color=C_BG_INPUT,
            button_color=C_BORDER,
            button_hover_color=C_ACCENT,
            dropdown_fg_color=C_BG_CARD,
            dropdown_hover_color=C_ACCENT,
            corner_radius=8,
            width=130,
            command=self._on_format_change
        )
        self.download_format_dropdown.grid(row=3, column=0, padx=16, pady=(0, 16), sticky="w")

        # ── Row 2-3: Video Quality
        self._make_option_label(self.options_card, "🎞️ Video Quality", 2, 1)
        self.video_quality_var = ctk.StringVar(value="Best")
        self.video_quality_dropdown = ctk.CTkOptionMenu(
            self.options_card,
            variable=self.video_quality_var,
            values=["Best", "1080p", "720p", "480p"],
            font=ctk.CTkFont(size=12),
            fg_color=C_BG_INPUT,
            button_color=C_BORDER,
            button_hover_color=C_ACCENT,
            dropdown_fg_color=C_BG_CARD,
            dropdown_hover_color=C_ACCENT,
            corner_radius=8,
            width=180,
        )
        self.video_quality_dropdown.grid(row=3, column=1, padx=16, pady=(0, 16), sticky="w")

    def _on_format_change(self, choice):
        """Disable quality dropdown if Audio is selected."""
        if choice == "Audio (M4A)":
            self.video_quality_dropdown.configure(state="disabled")
        else:
            self.video_quality_dropdown.configure(state="normal")

    def _make_option_label(self, parent, text: str, row: int, col: int):
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C_TEXT_DIM,
        )
        label.grid(row=row, column=col, sticky="w", padx=16, pady=(10, 2))

    def _build_output_section(self, row: int):
        """Transcript output textbox."""
        self.output_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=C_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=C_BORDER,
        )
        self.output_card.grid(row=row, column=0, sticky="nsew", pady=(0, 8))
        self.output_card.columnconfigure(0, weight=1)
        self.output_card.rowconfigure(1, weight=1)
        self.main_frame.rowconfigure(row, weight=1)

        # Output header
        output_header = ctk.CTkFrame(self.output_card, fg_color="transparent")
        output_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 4))

        ctk.CTkLabel(
            output_header,
            text="📝 Transcript Output",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_TEXT_DIM,
        ).pack(side="left")

        self.word_count_label = ctk.CTkLabel(
            output_header,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=C_TEXT_DIM,
        )
        self.word_count_label.pack(side="right")

        # Textbox
        self.output_text = ctk.CTkTextbox(
            self.output_card,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=C_BG_INPUT,
            text_color=C_TEXT,
            border_width=0,
            corner_radius=8,
            wrap="word",
            activate_scrollbars=True,
        )
        self.output_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))

        # Placeholder
        self._show_placeholder()

    def _show_placeholder(self):
        """Show placeholder text."""
        self.output_text.configure(text_color=C_TEXT_DIM)
        self.output_text.delete("1.0", "end")
        placeholder = (
            "Chào bạn! Mình là YouTube Knowledge Clipper\n\n"
            "Bước 1: 🔗 Paste YouTube URL\n"
            "Bước 2: ⚙️ Chọn options\n"
            "Bước 3: ⚡ Bấm \"Get Transcript\"\n"
        )
        self.output_text.insert("1.0", placeholder)

    def _build_action_buttons(self, row: int):
        """Action buttons."""
        self.btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.btn_frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))

        buttons = [
            ("📋 Copy", C_ACCENT, self._on_copy),
            ("💾 Save TXT", "#2d6a4f", self._on_save_txt),
            ("📝 Save MD", "#6d28d9", self._on_save_markdown),
            ("🎬 Save SRT", C_ORANGE, self._on_save_srt),
            ("🗑️ Clear", "#6e7681", self._on_clear),
        ]

        self.action_buttons = []
        for text, color, cmd in buttons:
            btn = ctk.CTkButton(
                self.btn_frame,
                text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                height=38,
                fg_color=color,
                hover_color=self._lighten_color(color),
                corner_radius=10,
                command=cmd,
            )
            btn.pack(side="left", padx=(0, 8), expand=True, fill="x")
            self.action_buttons.append(btn)

    def _build_status_bar(self, row: int):
        """Status bar."""
        self.status_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=C_BG_CARD,
            corner_radius=8,
            height=38,
        )
        self.status_frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="✅ Ready — Paste a YouTube URL to get started!",
            font=ctk.CTkFont(size=12),
            text_color=C_ACCENT_2,
            anchor="w",
        )
        self.status_label.pack(side="left", padx=16, pady=6)

        # Progress bar (hidden)
        self.progress_bar = ctk.CTkProgressBar(
            self.status_frame,
            mode="indeterminate",
            height=3,
            progress_color=C_ACCENT,
            fg_color=C_BG_INPUT,
            corner_radius=2,
        )

    # ═════════════════════════════════════════════════════════════
    #  ACTIONS
    # ═════════════════════════════════════════════════════════════

    def _set_status(self, text: str, color: str = C_TEXT_DIM):
        """Update status bar (thread-safe)."""
        def _update():
            self.status_label.configure(text=text, text_color=color)
        self.after(0, _update)

    def _set_processing(self, active: bool, button: str = "all"):
        """Enable/disable processing state (thread-safe)."""
        def _update():
            self.is_processing = active
            if active:
                if button in ("all", "transcript"):
                    self.get_btn.configure(state="disabled", text="⏳ Processing...")
                if button in ("all", "video"):
                    self.download_video_btn.configure(state="disabled", text="⏳ Downloading...")
                self.progress_bar.pack(side="right", padx=16, fill="x", expand=True)
                self.progress_bar.start()
            else:
                self.get_btn.configure(state="normal", text="⚡ Get Transcript")
                self.download_video_btn.configure(state="normal", text="⬇️ Download")
                self.progress_bar.stop()
                self.progress_bar.pack_forget()
        self.after(0, _update)

    def _set_output(self, text: str):
        """Set output textbox content (thread-safe)."""
        def _update():
            self.output_text.configure(text_color=C_TEXT)
            self.output_text.delete("1.0", "end")
            self.output_text.insert("1.0", text)
            words = len(text.split())
            lines = text.count("\n") + 1
            self.word_count_label.configure(text=f"{words:,} words  •  {lines:,} lines")
        self.after(0, _update)

    def _refresh_output(self):
        """Re-render the transcript with current timestamp setting."""
        if not self.current_segments:
            return
        show_ts = self.show_timestamps_var.get()
        formatted = format_transcript_text(self.current_segments, include_timestamps=show_ts)
        self._set_output(formatted)

    def _on_toggle_timestamps(self):
        """Handle timestamp toggle switch."""
        self._refresh_output()

    def _on_global_hotkey(self):
        """Handle Ctrl+Shift+C global hotkey to copy and fill URL."""
        if self.is_processing:
            return
            
        # 1. Send Ctrl+C to copy selected text
        keyboard.send('ctrl+c')
        time.sleep(0.1)  # Wait for clipboard to update
        
        # 2. Get text from clipboard
        try:
            url = pyperclip.paste().strip()
        except Exception:
            return
            
        if not url:
            return
            
        # 3. Only process if it looks like a YouTube URL
        if "youtube.com" in url or "youtu.be" in url:
            # We must use self.after to run UI updates in the main thread
            self.after(0, lambda: self._fill_and_process(url))
            
    def _fill_and_process(self, url: str):
        """Fill URL entry and bring app to front."""
        # Bring window to front
        self.deiconify()
        self.lift()
        self.focus_force()
        self.attributes('-topmost', True)
        self.after(500, lambda: self.attributes('-topmost', False))
        
        # Fill entry
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, url)

    def _on_get_transcript(self):
        """Handle Get Transcript button click."""
        if self.is_processing:
            return

        url = self.url_entry.get().strip()
        if not url:
            self._set_status("⚠️ Vui lòng nhập YouTube URL", C_ORANGE)
            return

        try:
            video_id = extract_video_id(url)
        except ValueError as e:
            self._set_status(f"❌ {str(e).split(chr(10))[0]}", C_RED)
            messagebox.showerror("URL không hợp lệ", str(e))
            return

        mode = self.mode_var.get()
        language = self.language_var.get().lower()
        if language == "auto":
            language = "auto"

        thread = threading.Thread(
            target=self._process_transcript,
            args=(url, video_id, mode, language),
            daemon=True,
        )
        thread.start()

    def _on_download_video(self):
        """Handle Download Video button click."""
        if self.is_processing:
            return

        url = self.url_entry.get().strip()
        if not url:
            self._set_status("⚠️ Vui lòng nhập YouTube URL", C_ORANGE)
            return

        try:
            video_id = extract_video_id(url)
        except ValueError as e:
            self._set_status(f"❌ {str(e).split(chr(10))[0]}", C_RED)
            messagebox.showerror("URL không hợp lệ", str(e))
            return

        thread = threading.Thread(
            target=self._process_download_video,
            args=(url,),
            daemon=True,
        )
        thread.start()

    def _process_download_video(self, url: str):
        """Process video downloading (background thread)."""
        self._set_processing(True, button="video")
        
        format_type = self.download_format_var.get()
        quality = self.video_quality_var.get()
        
        try:
            self._set_status("⬇️ Đang khởi tạo tải xuống...", C_ACCENT)
            
            file_path, title = download_video(
                url,
                format_type=format_type,
                quality=quality,
                progress_callback=lambda msg: self._set_status(f"⬇️ {msg}", C_ACCENT)
            )
            
            self._set_status(f"🎉 Đã tải xong: {title}", C_ACCENT_2)
            
            # Prompt user to open the folder
            def ask_open():
                if messagebox.askyesno("Tải hoàn tất", f"Đã tải thành công:\n{title}\n\nBạn có muốn mở thư mục chứa file không?"):
                    try:
                        folder = str(Path(file_path).parent)
                        os.startfile(folder)
                    except Exception as e:
                        print(f"Cannot open folder: {e}")
                        
            self.after(500, ask_open)
            
        except VideoDownloadError as e:
            self._set_status("❌ Lỗi tải file", C_RED)
            self.after(0, lambda: messagebox.showerror("Lỗi Tải Xuống", str(e)))
        except Exception as e:
            self._set_status(f"❌ Lỗi: {str(e)[:80]}", C_RED)
            self.after(0, lambda: messagebox.showerror("Lỗi", str(e)))
        finally:
            self._set_processing(False)

    def _process_transcript(self, url: str, video_id: str, mode: str, language: str):
        """Process transcript fetching (background thread)."""
        self._set_processing(True, button="transcript")

        try:
            segments = None
            used_mode = ""

            if mode in ("Auto", "Transcript Only"):
                self._set_status("🔍 Đang kiểm tra transcript...", C_ACCENT)
                try:
                    segments = get_youtube_transcript(url, language)
                    used_mode = "YouTube Transcript"
                    self._set_status(
                        f"✅ Transcript tìm thấy! ({len(segments)} segments)",
                        C_ACCENT_2,
                    )
                except TranscriptNotFoundError as e:
                    if mode == "Transcript Only":
                        raise
                    self._set_status(
                        "⚠️ Không có transcript. Chuyển sang Speech-to-Text...",
                        C_ORANGE,
                    )

            if segments is None:
                segments = self._run_speech_to_text(url, language)
                used_mode = "Speech-to-Text"

            if segments:
                self.current_segments = segments
                self.current_metadata = {
                    "url": url,
                    "video_id": video_id,
                    "language": language,
                    "mode": used_mode,
                    "date": get_current_date(),
                    "title": f"YouTube Video {video_id}",
                }

                try:
                    info = get_video_info(url)
                    if info.get("title") and info["title"] != "Unknown":
                        self.current_metadata["title"] = info["title"]
                except Exception:
                    pass

                show_ts = self.show_timestamps_var.get()
                formatted = format_transcript_text(segments, include_timestamps=show_ts)
                self._set_output(formatted)

                self._set_status(
                    f"🎉 Hoàn tất! {len(segments)} segments — {used_mode}",
                    C_ACCENT_2,
                )

        except TranscriptNotFoundError as e:
            self._set_status(f"❌ {str(e).split(chr(10))[0]}", C_RED)
            self.after(0, lambda: messagebox.showwarning("Không có Transcript", str(e)))
        except AudioDownloadError as e:
            self._set_status("❌ Lỗi tải audio", C_RED)
            self.after(0, lambda: messagebox.showerror("Lỗi Audio", str(e)))
        except WhisperTranscriptionError as e:
            self._set_status("❌ Lỗi speech-to-text", C_RED)
            self.after(0, lambda: messagebox.showerror("Lỗi Whisper", str(e)))
        except Exception as e:
            self._set_status(f"❌ Lỗi: {str(e)[:80]}", C_RED)
            self.after(0, lambda: messagebox.showerror("Lỗi", str(e)))
        finally:
            self._set_processing(False)

    def _run_speech_to_text(self, url: str, language: str) -> list[dict]:
        """Download audio and run whisper transcription."""
        if get_ffmpeg_path() is None:
            raise AudioDownloadError(
                "FFmpeg không tìm thấy.\n"
                "Đặt ffmpeg.exe vào thư mục 'ffmpeg/' cạnh ứng dụng,\n"
                "hoặc cài ffmpeg vào system PATH."
            )

        self._set_status("⬇️ Đang tải audio từ YouTube...", C_ACCENT)
        audio_path, title = download_audio(
            url,
            progress_callback=lambda msg: self._set_status(f"⬇️ {msg}", C_ACCENT),
        )

        self.current_metadata = self.current_metadata or {}
        self.current_metadata["title"] = title

        self._set_status("🎤 Đang chạy Speech-to-Text...", C_PURPLE)
        model_size = self.whisper_model_var.get()
        whisper_lang = None if language == "auto" else language

        segments = transcribe_audio(
            audio_path,
            model_size=model_size,
            language=whisper_lang,
            progress_callback=lambda msg: self._set_status(f"🎤 {msg}", C_PURPLE),
        )

        return segments

    def _on_copy(self):
        """Copy transcript to clipboard."""
        text = self.output_text.get("1.0", "end").strip()
        if not text or text.startswith("Chào bạn"):
            self._set_status("⚠️ Không có transcript để copy", C_ORANGE)
            return

        try:
            import pyperclip
            pyperclip.copy(text)
        except ImportError:
            self.clipboard_clear()
            self.clipboard_append(text)

        self._set_status("📋 Đã copy transcript vào clipboard!", C_ACCENT_2)

    def _on_save_txt(self):
        self._save_file("txt", export_txt)

    def _on_save_markdown(self):
        self._save_file("md", export_markdown)

    def _on_save_srt(self):
        self._save_file("srt", export_srt)

    def _save_file(self, ext: str, export_func):
        """Generic save file handler."""
        if not self.current_segments:
            self._set_status("⚠️ Không có transcript để lưu", C_ORANGE)
            return

        title = self.current_metadata.get("title", "transcript")
        default_name = sanitize_filename(title)

        type_names = {
            "txt": "Text Files",
            "md": "Markdown Files",
            "srt": "SRT Subtitle Files",
        }

        file_path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            initialdir=str(get_base_dir() / "exports"),
            initialfile=f"{default_name}.{ext}",
            filetypes=[(type_names.get(ext, "Files"), f"*.{ext}"), ("All Files", "*.*")],
            title=f"Save as .{ext.upper()}",
        )

        if not file_path:
            return

        try:
            export_func(self.current_segments, file_path, self.current_metadata)
            self._set_status(f"💾 Đã lưu: {Path(file_path).name}", C_ACCENT_2)
        except PermissionError:
            self._set_status("❌ Không có quyền ghi file", C_RED)
            messagebox.showerror("Lỗi", "Không có quyền ghi vào thư mục này.")
        except Exception as e:
            self._set_status("❌ Lỗi lưu file", C_RED)
            messagebox.showerror("Lỗi lưu file", str(e))

    def _on_clear(self):
        """Clear output and reset state."""
        self.current_segments = []
        self.current_metadata = {}
        self.word_count_label.configure(text="")
        self._show_placeholder()
        self._set_status("✅ Ready — Paste a YouTube URL to get started!", C_ACCENT_2)

    # ═════════════════════════════════════════════════════════════
    #  UTILITIES
    # ═════════════════════════════════════════════════════════════

    @staticmethod
    def _lighten_color(hex_color: str) -> str:
        try:
            hex_color = hex_color.lstrip("#")
            r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            r = min(255, int(r + (255 - r) * 0.25))
            g = min(255, int(g + (255 - g) * 0.25))
            b = min(255, int(b + (255 - b) * 0.25))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color


# ═════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═════════════════════════════════════════════════════════════════

def main():
    app = YouTubeKnowledgeClipperApp()
    app.mainloop()


if __name__ == "__main__":
    main()

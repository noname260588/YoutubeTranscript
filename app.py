"""
YouTube Knowledge Clipper — Main Application
Desktop app for extracting YouTube transcripts and speech-to-text.
Built with CustomTkinter for a modern dark UI.
"""

import os
import re
import sys
import threading
import time
import math
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

import customtkinter as ctk

class MyCTkButton(ctk.CTkButton):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("cursor", "hand2")
        super().__init__(*args, **kwargs)

class MyCTkOptionMenu(ctk.CTkOptionMenu):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("cursor", "hand2")
        super().__init__(*args, **kwargs)

try:
    import keyboard
    HAS_KEYBOARD = True
except Exception as e:
    print(f"Keyboard module disabled (likely requires root on Mac/Linux): {e}")
    HAS_KEYBOARD = False
import pyperclip

from utils import (
    extract_video_id,
    ensure_dirs,
    get_base_dir,
    get_asset_path,
    sanitize_filename,
    get_current_date,
    get_ffmpeg_path,
)
from transcript_service import get_youtube_transcript, TranscriptNotFoundError
from audio_service import (
    download_audio,
    AudioDownloadCancelledError,
    AudioDownloadError,
)
from video_service import download_video, VideoDownloadCancelledError, VideoDownloadError
from whisper_service import transcribe_audio, WhisperTranscriptionError
from export_service import (
    MARKDOWN_MODES,
    export_txt,
    export_markdown,
    export_srt,
    format_clean_transcript_text,
    format_transcript_text,
)
from settings_service import load_settings, save_settings
from services.youtube_metadata_service import (
    clean_youtube_description,
    extract_chapters_from_description,
    get_youtube_metadata,
)
from services.prompt_template_service import (
    get_template,
    list_templates,
    render_prompt,
)


# ─── App Constants ───────────────────────────────────────────────
APP_TITLE = "YouTube Knowledge Clipper"
APP_VERSION = "1.0.0"
WINDOW_WIDTH = 980
WINDOW_HEIGHT = 720
OUTPUT_DEFAULT_HEIGHT = 180
OUTPUT_EXPANDED_HEIGHT = 280

LANGUAGES = ["Auto", "vi", "en", "ja", "zh"]
MODES = ["Auto", "Transcript Only", "Speech-to-Text Only"]
WHISPER_MODELS = ["tiny", "base", "small", "medium"]
COOKIE_BROWSERS = ["Auto", "None", "Edge", "Chrome", "Firefox", "Brave", "Vivaldi", "Opera"]

# ─── Color Palette ───────────────────────────────────────────────
C_BG_DARK = "#0a0e17"
C_BG_CARD = "#161b22"
C_BG_INPUT = "#1c2333"
C_BG_ELEVATED = "#20283a"
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
        self.minsize(860, 620)
        self.configure(fg_color=C_BG_DARK)

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - WINDOW_WIDTH) // 2
        y = (self.winfo_screenheight() - WINDOW_HEIGHT) // 2
        self.geometry(f"+{x}+{y}")

        # App icon
        try:
            icon_path = get_asset_path("icon.ico")
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        # ─── State ───────────────────────────────────────────────
        self.current_segments: list[dict] = []
        self.current_metadata: dict = {}
        self.is_processing = False
        self.cancel_event = threading.Event()
        self.settings = load_settings()
        self.prompt_templates = self._load_prompt_templates()

        # ─── Ensure Directories ──────────────────────────────────
        ensure_dirs()

        # ─── Set Appearance ──────────────────────────────────────
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Register global hotkey (Ctrl + Shift + C) to grab URL from clipboard
        if HAS_KEYBOARD:
            try:
                keyboard.add_hotkey('ctrl+shift+c', self._on_global_hotkey)
            except Exception as e:
                print(f"Could not register global hotkey: {e}")

        # ─── Build UI ────────────────────────────────────────────
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)





    # ═════════════════════════════════════════════════════════════
    #  UI BUILDING
    # ═════════════════════════════════════════════════════════════

    def _load_prompt_templates(self) -> list[dict]:
        """Load prompt template metadata for the UI."""
        try:
            return list_templates()
        except Exception as e:
            print(f"Cannot load prompt templates: {e}")
            return []

    def _build_ui(self):
        """Build the complete UI layout."""
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=14, pady=8)

        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(3, weight=4, minsize=OUTPUT_DEFAULT_HEIGHT)

        self._build_header(row=0)
        self._build_input_section(row=1)
        self._build_options_section(row=2)
        self._build_output_section(row=3)
        self._build_action_buttons(row=4)
        self._build_prompt_section(row=4)
        self._build_status_bar(row=5)

    def _build_header(self, row: int):
        """Header section."""
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))

        # Small corner app icon
        try:
            from PIL import Image
            icon_path = get_asset_path("icon.ico")
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

        title_stack = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_stack.pack(side="left", fill="x", expand=True)

        title_row = ctk.CTkFrame(title_stack, fg_color="transparent")
        title_row.pack(anchor="w")

        self.title_label = ctk.CTkLabel(
            title_row,
            text="YouTube Knowledge Clipper",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=C_TEXT,
        )
        self.title_label.pack(side="left")

        version_label = ctk.CTkLabel(
            title_row,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color=C_TEXT_DIM,
            fg_color=C_BG_CARD,
            corner_radius=8,
            padx=8,
            pady=2,
        )
        version_label.pack(side="left", padx=(10, 0))

        subtitle_label = ctk.CTkLabel(
            title_stack,
            text="Transcript, video download và Speech-to-Text trong một màn hình",
            font=ctk.CTkFont(size=11),
            text_color=C_TEXT_DIM,
        )
        subtitle_label.pack(anchor="w", pady=(1, 0))

        # About button
        self.about_btn = MyCTkButton(
            header_frame,
            text="ℹ️ About",
            width=82,
            height=28,
            fg_color="transparent",
            hover_color=C_BORDER,
            text_color=C_TEXT_DIM,
            command=self._show_about
        )
        self.about_btn.pack(side="right")

        # Tutorial button
        self.tutorial_btn = MyCTkButton(
            header_frame,
            text="📖 Hướng dẫn",
            width=106,
            height=28,
            fg_color="transparent",
            hover_color=C_BORDER,
            text_color=C_TEXT_DIM,
            command=self._show_tutorial
        )
        self.tutorial_btn.pack(side="right", padx=(0, 5))

        self.settings_btn = MyCTkButton(
            header_frame,
            text="⚙️ Settings",
            width=92,
            height=28,
            fg_color="transparent",
            hover_color=C_BORDER,
            text_color=C_TEXT_DIM,
            command=self._show_settings,
        )
        self.settings_btn.pack(side="right", padx=(0, 5))

    def _build_input_section(self, row: int):
        """URL input + Get Transcript button."""
        self.input_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=C_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=C_BORDER,
        )
        self.input_card.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        self.input_card.columnconfigure(0, weight=1)

        self.input_card.columnconfigure(1, weight=0)
        self.input_card.columnconfigure(2, weight=0)

        url_label = ctk.CTkLabel(
            self.input_card,
            text="🔗 YouTube URL",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_TEXT_DIM,
        )
        url_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(8, 3))

        self.url_entry = ctk.CTkEntry(
            self.input_card,
            placeholder_text="Dán link YouTube vào đây...",
            font=ctk.CTkFont(size=12),
            height=36,
            fg_color=C_BG_INPUT,
            border_color=C_BORDER,
            text_color=C_TEXT,
            corner_radius=10,
        )
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=(14, 6), pady=(0, 7))
        self.url_entry.bind("<Return>", lambda e: self._on_get_transcript())

        self.paste_url_btn = MyCTkButton(
            self.input_card,
            text="📋 Dán",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            width=86,
            fg_color=C_BG_ELEVATED,
            hover_color=C_BORDER,
            text_color=C_TEXT,
            corner_radius=10,
            command=self._on_paste_url,
        )
        self.paste_url_btn.grid(row=1, column=1, sticky="e", padx=(0, 6), pady=(0, 7))

        self.clear_url_btn = MyCTkButton(
            self.input_card,
            text="✕",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=36,
            width=46,
            fg_color=C_BG_ELEVATED,
            hover_color=C_BORDER,
            text_color=C_TEXT_DIM,
            corner_radius=10,
            command=self._on_clear_url,
        )
        self.clear_url_btn.grid(row=1, column=2, sticky="e", padx=(0, 14), pady=(0, 7))
        self.url_utility_buttons = [self.paste_url_btn, self.clear_url_btn]

        action_row = ctk.CTkFrame(self.input_card, fg_color="transparent")
        action_row.grid(row=2, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 9))
        action_row.columnconfigure(0, weight=1, uniform="input_actions")
        action_row.columnconfigure(1, weight=1, uniform="input_actions")
        action_row.columnconfigure(2, weight=0)

        self.get_btn = MyCTkButton(
            action_row,
            text="⚡ Lấy Transcript",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            fg_color=C_ACCENT,
            hover_color=C_ACCENT_HOVER,
            corner_radius=10,
            command=self._on_get_transcript,
        )
        self.get_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.download_video_btn = MyCTkButton(
            action_row,
            text="⬇️ Tải Video",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            fg_color=C_PURPLE,
            hover_color=self._lighten_color(C_PURPLE),
            corner_radius=10,
            command=self._on_download_video,
        )
        self.download_video_btn.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        self.cancel_btn = MyCTkButton(
            action_row,
            text="⛔ Hủy",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            width=112,
            fg_color=C_RED,
            hover_color=self._lighten_color(C_RED),
            corner_radius=10,
            state="disabled",
            command=self._on_cancel_processing,
        )
        self.cancel_btn.grid(row=0, column=2, sticky="e")

    def _build_options_section(self, row: int):
        """Options: Language, Mode, Whisper settings, Show timestamps toggle."""
        self.options_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=C_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=C_BORDER,
        )
        self.options_card.grid(row=row, column=0, sticky="ew", pady=(0, 6))

        for i in range(6):
            self.options_card.columnconfigure(i, weight=1, uniform="options")

        self._make_option_label(self.options_card, "🌐 Language", 0, 0)
        language_value = self.settings.get("selected_language", "Auto")
        if language_value not in LANGUAGES:
            language_value = "Auto"
        self.language_var = ctk.StringVar(value=language_value)
        self.language_dropdown = MyCTkOptionMenu(
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
            width=160,
            command=lambda _choice: self._save_current_preferences(),
        )
        self.language_dropdown.grid(row=1, column=0, sticky="ew", padx=(14, 5), pady=(0, 6))

        self._make_option_label(self.options_card, "⚙️ Mode", 0, 1)
        mode_value = self.settings.get("selected_mode", "Auto")
        if mode_value not in MODES:
            mode_value = "Auto"
        self.mode_var = ctk.StringVar(value=mode_value)
        self.mode_dropdown = MyCTkOptionMenu(
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
            command=lambda _choice: self._save_current_preferences(),
        )
        self.mode_dropdown.grid(row=1, column=1, sticky="ew", padx=5, pady=(0, 6))

        self._make_option_label(self.options_card, "🤖 Whisper", 0, 2)
        whisper_model_value = self.settings.get("selected_whisper_model", "small")
        if whisper_model_value not in WHISPER_MODELS:
            whisper_model_value = "small"
        self.whisper_model_var = ctk.StringVar(value=whisper_model_value)
        self.whisper_model_dropdown = MyCTkOptionMenu(
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
            width=160,
            command=lambda _choice: self._save_current_preferences(),
        )
        self.whisper_model_dropdown.grid(row=1, column=2, sticky="ew", padx=5, pady=(0, 6))

        self._make_option_label(self.options_card, "📥 Format", 0, 3)
        self.download_format_var = ctk.StringVar(value="Video (MP4)")
        self.download_format_dropdown = MyCTkOptionMenu(
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
        self.download_format_dropdown.grid(row=1, column=3, sticky="ew", padx=5, pady=(0, 6))

        self._make_option_label(self.options_card, "🎞️ Quality", 0, 4)
        self.video_quality_var = ctk.StringVar(value="480p")
        self.video_quality_dropdown = MyCTkOptionMenu(
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
        self.video_quality_dropdown.grid(row=1, column=4, sticky="ew", padx=5, pady=(0, 6))

        self._make_option_label(self.options_card, "🍪 Cookies", 0, 5)
        self.cookie_browser_var = ctk.StringVar(value="Auto")
        self.cookie_browser_dropdown = MyCTkOptionMenu(
            self.options_card,
            variable=self.cookie_browser_var,
            values=COOKIE_BROWSERS,
            font=ctk.CTkFont(size=12),
            fg_color=C_BG_INPUT,
            button_color=C_BORDER,
            button_hover_color=C_ACCENT,
            dropdown_fg_color=C_BG_CARD,
            dropdown_hover_color=C_ACCENT,
            corner_radius=8,
            width=150,
        )
        self.cookie_browser_dropdown.grid(row=1, column=5, sticky="ew", padx=(5, 14), pady=(0, 6))

        self.show_timestamps_var = ctk.BooleanVar(value=bool(self.settings.get("show_timestamps", True)))
        self.timestamps_switch = ctk.CTkSwitch(
            self.options_card,
            text="Hiện timestamp",
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
        self.timestamps_switch.grid(row=2, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 7))

        self.device_label = ctk.CTkLabel(
            self.options_card,
            text="CPU • int8",
            font=ctk.CTkFont(size=12),
            text_color=C_TEXT_DIM,
            fg_color=C_BG_INPUT,
            corner_radius=8,
            padx=10,
            pady=4,
        )
        self.device_label.grid(row=2, column=5, sticky="e", padx=(5, 14), pady=(0, 7))

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
        left_pad = 14 if col == 0 else 5
        right_pad = 14 if col == 5 else 5
        label.grid(row=row, column=col, sticky="w", padx=(left_pad, right_pad), pady=(7, 2))

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
        self.output_card.rowconfigure(2, weight=1, minsize=OUTPUT_DEFAULT_HEIGHT)
        self.main_frame.rowconfigure(row, weight=4, minsize=OUTPUT_DEFAULT_HEIGHT)

        # Output header
        output_header = ctk.CTkFrame(self.output_card, fg_color="transparent")
        output_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(6, 2))

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

        self.output_state_label = ctk.CTkLabel(
            output_header,
            text="Chưa có transcript",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C_TEXT_DIM,
            fg_color=C_BG_INPUT,
            corner_radius=8,
            padx=8,
            pady=2,
        )
        self.output_state_label.pack(side="right", padx=(0, 10))

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
            height=OUTPUT_DEFAULT_HEIGHT,
        )
        self.output_text.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))

        self.download_wait_frame = ctk.CTkFrame(
            self.output_card,
            fg_color=C_BG_INPUT,
            corner_radius=8,
            border_width=0,
        )
        self.download_wait_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.download_wait_frame.grid_columnconfigure(0, weight=1)
        self.download_wait_frame.grid_rowconfigure(1, weight=1)
        self.download_wait_frame.grid_remove()

        self.download_wait_title = ctk.CTkLabel(
            self.download_wait_frame,
            text="Đang chuẩn bị tải video",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=C_TEXT,
            wraplength=680,
        )
        self.download_wait_title.grid(row=0, column=0, sticky="ew", padx=16, pady=(18, 4))

        self.download_wait_canvas = tk.Canvas(
            self.download_wait_frame,
            bg=C_BG_INPUT,
            highlightthickness=0,
            bd=0,
        )
        self.download_wait_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)

        self.download_wait_status = ctk.CTkLabel(
            self.download_wait_frame,
            text="Neon Download Portal",
            font=ctk.CTkFont(size=12),
            text_color=C_TEXT_DIM,
            wraplength=720,
            justify="center",
        )
        self.download_wait_status.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 10))

        self.download_wait_active = False
        self.download_wait_step = 0
        self.download_wait_job = None

        # Placeholder
        self._show_placeholder()

    def _show_placeholder(self):
        """Show placeholder text."""
        self._hide_download_waiting()
        self._set_output_expanded(False)
        self.output_text.tkraise()
        self.output_text.configure(text_color=C_TEXT_DIM)
        self.output_text.delete("1.0", "end")
        placeholder = (
            "Chưa có transcript\n\n"
            "Dán link YouTube để bắt đầu. Kết quả transcript sẽ xuất hiện ở đây."
        )
        self.output_text.insert("1.0", placeholder)
        if hasattr(self, "output_state_label"):
            self.output_state_label.configure(text="Chưa có transcript", text_color=C_TEXT_DIM)
        if hasattr(self, "word_count_label"):
            self.word_count_label.configure(text="")
        self._sync_output_actions()

    def _set_output_expanded(self, expanded: bool):
        """Resize the transcript area so fetched content is immediately readable."""
        height = OUTPUT_EXPANDED_HEIGHT if expanded else OUTPUT_DEFAULT_HEIGHT
        weight = 6 if expanded else 4
        try:
            self.main_frame.rowconfigure(3, weight=weight, minsize=height)
            self.output_card.rowconfigure(2, weight=1, minsize=height)
            self.output_text.configure(height=height)
        except Exception:
            pass

    def _show_output_loading(self, title: str, detail: str = ""):
        """Show a lightweight loading message in the transcript output area."""
        def _update():
            self.download_wait_active = False
            try:
                self.download_wait_frame.grid_remove()
            except Exception:
                pass
            self._set_output_expanded(False)
            self.output_text.tkraise()
            self.output_text.configure(text_color=C_TEXT_DIM)
            self.output_text.delete("1.0", "end")
            message = title.strip()
            if detail:
                message = f"{message}\n\n{detail.strip()}"
            self.output_text.insert("1.0", message)
            self.word_count_label.configure(text="")
            self.output_state_label.configure(text=title, text_color=C_ACCENT)
            self._sync_output_actions()
        self.after(0, _update)

    def _show_download_waiting(self, title: str = "Đang tải video") -> None:
        """Show a lightweight waiting animation while yt-dlp is downloading."""
        def _update():
            self.download_wait_title.configure(text=title)
            self.download_wait_status.configure(text="Đang kết nối YouTube...")
            self.output_state_label.configure(text="Đang tải", text_color=C_ACCENT)
            self.download_wait_active = True
            self.download_wait_step = 0
            self.download_wait_frame.grid()
            self.download_wait_frame.tkraise()
            self._animate_download_waiting()
        self.after(0, _update)

    def _hide_download_waiting(self) -> None:
        """Hide and stop the download waiting animation."""
        def _update():
            self.download_wait_active = False
            if self.download_wait_job is not None:
                try:
                    self.after_cancel(self.download_wait_job)
                except Exception:
                    pass
                self.download_wait_job = None
            try:
                self.download_wait_canvas.delete("all")
                self.download_wait_frame.grid_remove()
            except Exception:
                pass
            if hasattr(self, "output_state_label"):
                if self.current_segments:
                    self.output_state_label.configure(text="Có transcript", text_color=C_ACCENT_2)
                else:
                    self.output_state_label.configure(text="Chưa có transcript", text_color=C_TEXT_DIM)
        self.after(0, _update)

    def _update_download_waiting_status(self, text: str, progress: float | None = None) -> None:
        """Update the waiting animation caption from worker threads."""
        def _update():
            if not self.download_wait_active:
                return
            if progress is None:
                self.download_wait_status.configure(text=text)
            else:
                self.download_wait_status.configure(text=f"{text}  •  {int(progress * 100)}%")
        self.after(0, _update)

    def _animate_download_waiting(self) -> None:
        """Animate a neon download portal in the output panel."""
        if not self.download_wait_active:
            return

        canvas = self.download_wait_canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 360)
        height = max(canvas.winfo_height(), 180)
        center_x = width / 2
        center_y = height / 2
        step = self.download_wait_step
        pulse = (math.sin(step * 0.22) + 1) / 2

        # Moving neon grid background.
        horizon_y = center_y + 80
        for index in range(12):
            y = horizon_y - ((index * 22 + step * 3) % 220)
            alpha_color = "#17243b" if index % 2 else "#1d3354"
            canvas.create_line(0, y, width, y, fill=alpha_color, width=1)

        for index in range(-8, 9):
            base_x = center_x + index * 46
            offset = math.sin(step * 0.04) * 20
            canvas.create_line(
                center_x,
                center_y + 84,
                base_x + offset,
                height,
                fill="#132033",
                width=1,
            )

        # Portal rings.
        ring_rx = min(width * 0.24, 180)
        ring_ry = min(height * 0.26, 112)
        for ring_index, color in enumerate((C_ACCENT, C_PURPLE, C_ACCENT_2)):
            inset = ring_index * 18
            start = (step * (6 + ring_index * 3) + ring_index * 62) % 360
            extent = 82 + pulse * 34
            canvas.create_oval(
                center_x - ring_rx + inset,
                center_y - ring_ry + inset * 0.56,
                center_x + ring_rx - inset,
                center_y + ring_ry - inset * 0.56,
                outline="#0a1320",
                width=7 - ring_index,
            )
            canvas.create_arc(
                center_x - ring_rx + inset,
                center_y - ring_ry + inset * 0.56,
                center_x + ring_rx - inset,
                center_y + ring_ry - inset * 0.56,
                start=start,
                extent=extent,
                outline=color,
                width=4 - ring_index,
                style="arc",
            )
            canvas.create_arc(
                center_x - ring_rx + inset,
                center_y - ring_ry + inset * 0.56,
                center_x + ring_rx - inset,
                center_y + ring_ry - inset * 0.56,
                start=start + 180,
                extent=42,
                outline="#58a6ff",
                width=2,
                style="arc",
            )

        # Falling video frames pulled into the portal.
        for index in range(7):
            t = ((step * 0.018) + index / 7) % 1.0
            side = -1 if index % 2 else 1
            x = center_x + side * (width * 0.38) * (1 - t) + math.sin(step * 0.09 + index) * 18
            y = center_y - height * 0.42 + t * height * 0.78
            scale = 0.42 + t * 0.62
            card_w = 92 * scale
            card_h = 48 * scale
            skew = math.sin(step * 0.1 + index) * 12 * scale
            color = [C_ACCENT, C_PURPLE, C_ACCENT_2, C_ORANGE][index % 4]

            polygon = [
                x - card_w / 2 + skew,
                y - card_h / 2,
                x + card_w / 2 + skew,
                y - card_h / 2,
                x + card_w / 2 - skew,
                y + card_h / 2,
                x - card_w / 2 - skew,
                y + card_h / 2,
            ]
            canvas.create_polygon(
                [coord + 7 if pos % 2 == 0 else coord + 7 for pos, coord in enumerate(polygon)],
                fill="#07111f",
                outline="",
            )
            canvas.create_polygon(polygon, fill="#142238", outline="#0a1320", width=4)
            canvas.create_polygon(polygon, fill="#142238", outline=color, width=max(1, int(2 * scale)))

            play_x = x - card_w * 0.18
            play_y = y
            play_size = 8 * scale
            canvas.create_polygon(
                play_x - play_size / 2,
                play_y - play_size,
                play_x - play_size / 2,
                play_y + play_size,
                play_x + play_size,
                play_y,
                fill=color,
                outline="",
            )
            canvas.create_line(
                x + card_w * 0.04,
                y - card_h * 0.12,
                x + card_w * 0.34,
                y - card_h * 0.12,
                fill="#314563",
                width=max(1, int(2 * scale)),
            )
            canvas.create_line(
                x + card_w * 0.04,
                y + card_h * 0.12,
                x + card_w * 0.28,
                y + card_h * 0.12,
                fill="#314563",
                width=max(1, int(2 * scale)),
            )

        # Particle stream and central download symbol.
        for index in range(34):
            t = ((step * 0.035) + index / 34) % 1.0
            theta = index * 2.28 + step * 0.08
            radius = (1 - t) * min(width, height) * 0.44
            x = center_x + math.cos(theta) * radius
            y = center_y + math.sin(theta) * radius * 0.58
            dot_size = 1.4 + t * 3.2
            color = C_ACCENT_2 if index % 3 == 0 else C_ACCENT
            canvas.create_oval(x - dot_size, y - dot_size, x + dot_size, y + dot_size, fill=color, outline="")

        arrow_y = center_y - 12 + math.sin(step * 0.22) * 5
        arrow_color = C_ACCENT_2 if pulse > 0.48 else C_ACCENT
        canvas.create_line(center_x, arrow_y - 38, center_x, arrow_y + 12, fill="#07111f", width=12)
        canvas.create_line(center_x, arrow_y - 38, center_x, arrow_y + 12, fill=arrow_color, width=6)
        canvas.create_polygon(
            center_x - 22,
            arrow_y + 6,
            center_x + 22,
            arrow_y + 6,
            center_x,
            arrow_y + 34,
            fill=arrow_color,
            outline="#b6f7c4",
        )
        canvas.create_line(center_x - 36, arrow_y + 46, center_x + 36, arrow_y + 46, fill=arrow_color, width=5)

        self.download_wait_step += 1
        self.download_wait_job = self.after(36, self._animate_download_waiting)

    def _build_action_buttons(self, row: int):
        """Action buttons."""
        self.btn_frame = ctk.CTkFrame(self.output_card, fg_color="transparent")
        self.btn_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 5))

        buttons = [
            ("📋 Copy", C_ACCENT, self._on_copy, True),
            ("💾 Save TXT", "#2d6a4f", self._on_save_txt, True),
            ("📝 Save MD", "#6d28d9", self._on_save_markdown, True),
            ("🎬 Save SRT", C_ORANGE, self._on_save_srt, True),
            ("🗑️ Clear", "#6e7681", self._on_clear, False),
        ]

        self.action_buttons = []
        self.output_action_buttons = []
        for text, color, cmd, requires_output in buttons:
            btn = MyCTkButton(
                self.btn_frame,
                text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                height=28,
                fg_color=color,
                hover_color=self._lighten_color(color),
                corner_radius=8,
                command=cmd,
            )
            btn.pack(side="left", padx=(0, 6), expand=True, fill="x")
            self.action_buttons.append(btn)
            if requires_output:
                self.output_action_buttons.append(btn)

        self._sync_output_actions()

    def _build_prompt_section(self, row: int):
        """Prompt Template Generator section."""
        self.prompt_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=C_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=C_BORDER,
        )
        self.prompt_card.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        self.prompt_card.columnconfigure(2, weight=1)

        ctk.CTkLabel(
            self.prompt_card,
            text="🧩 Prompt Templates",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_TEXT_DIM,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(7, 2))

        template_names = [template["name"] for template in self.prompt_templates] or ["No templates"]
        self.prompt_template_name_to_id = {
            template["name"]: template["id"] for template in self.prompt_templates
        }
        self.prompt_template_var = ctk.StringVar(value=template_names[0])
        self.prompt_template_dropdown = MyCTkOptionMenu(
            self.prompt_card,
            variable=self.prompt_template_var,
            values=template_names,
            fg_color=C_BG_INPUT,
            button_color=C_BORDER,
            button_hover_color=C_ACCENT,
            dropdown_fg_color=C_BG_CARD,
            dropdown_hover_color=C_ACCENT,
            command=lambda _choice: self._on_prompt_template_selected(),
            width=190,
        )
        self.prompt_template_dropdown.grid(row=1, column=0, sticky="ew", padx=(12, 6), pady=(0, 6))

        self.prompt_transcript_mode_var = ctk.StringVar(value="Use Clean Transcript")
        self.prompt_transcript_mode_dropdown = MyCTkOptionMenu(
            self.prompt_card,
            variable=self.prompt_transcript_mode_var,
            values=["Use Clean Transcript", "Use Raw Transcript", "Use Transcript with timestamps"],
            fg_color=C_BG_INPUT,
            button_color=C_BORDER,
            button_hover_color=C_ACCENT,
            dropdown_fg_color=C_BG_CARD,
            dropdown_hover_color=C_ACCENT,
            width=190,
        )
        self.prompt_transcript_mode_dropdown.grid(row=1, column=1, sticky="w", padx=(0, 6), pady=(0, 6))

        self.prompt_description_label = ctk.CTkLabel(
            self.prompt_card,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=C_TEXT_DIM,
            anchor="w",
            wraplength=520,
        )
        self.prompt_description_label.grid(row=1, column=2, sticky="ew", padx=(0, 6), pady=(0, 6))

        button_frame = ctk.CTkFrame(self.prompt_card, fg_color="transparent")
        button_frame.grid(row=1, column=3, sticky="e", padx=(0, 12), pady=(0, 6))

        self.generate_prompt_btn = MyCTkButton(
            button_frame,
            text="Generate Prompt",
            width=118,
            height=30,
            command=self._on_generate_prompt,
        )
        self.generate_prompt_btn.pack(side="left", padx=(0, 6))

        self.copy_prompt_only_btn = MyCTkButton(
            button_frame,
            text="Copy Prompt Only",
            width=126,
            height=30,
            fg_color=C_BG_ELEVATED,
            hover_color=C_BORDER,
            command=self._on_copy_prompt_only,
        )
        self.copy_prompt_only_btn.pack(side="left", padx=(0, 6))

        self.copy_prompt_transcript_btn = MyCTkButton(
            button_frame,
            text="Copy + Transcript",
            width=128,
            height=30,
            fg_color=C_PURPLE,
            hover_color=self._lighten_color(C_PURPLE),
            command=self._on_copy_prompt_with_transcript,
        )
        self.copy_prompt_transcript_btn.pack(side="left")

        self.prompt_preview_text = ctk.CTkTextbox(
            self.prompt_card,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=C_BG_INPUT,
            text_color=C_TEXT,
            border_width=0,
            corner_radius=8,
            wrap="word",
            height=82,
            activate_scrollbars=True,
        )
        self.prompt_preview_text.grid(row=2, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 10))

        self.prompt_controls = [
            self.prompt_template_dropdown,
            self.prompt_transcript_mode_dropdown,
            self.generate_prompt_btn,
            self.copy_prompt_only_btn,
            self.copy_prompt_transcript_btn,
        ]

        if not self.prompt_templates:
            for control in self.prompt_controls:
                control.configure(state="disabled")
            self.prompt_description_label.configure(text="prompt_templates.json không khả dụng.")
        else:
            self._on_prompt_template_selected()

    def _build_status_bar(self, row: int):
        """Status bar."""
        self.status_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=C_BG_CARD,
            corner_radius=8,
            height=34,
        )
        self.status_frame.grid(row=row, column=0, sticky="ew", pady=(0, 2))
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="✅ Sẵn sàng — dán YouTube URL để bắt đầu",
            font=ctk.CTkFont(size=12),
            text_color=C_ACCENT_2,
            anchor="w",
            wraplength=600,
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=12, pady=4)

        self.progress_value_label = ctk.CTkLabel(
            self.status_frame,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C_TEXT_DIM,
            width=48,
        )
        self.progress_value_label.grid(row=0, column=2, padx=(8, 12), pady=4)
        self.progress_value_label.grid_remove()

        # Progress bar (hidden)
        self.progress_bar = ctk.CTkProgressBar(
            self.status_frame,
            mode="indeterminate",
            height=5,
            width=180,
            progress_color=C_ACCENT,
            fg_color=C_BG_INPUT,
            corner_radius=2,
        )
        self.progress_bar.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=4)
        self.progress_bar.grid_remove()
        self.status_frame.bind(
            "<Configure>",
            lambda event: self.status_label.configure(wraplength=max(event.width - 310, 280)),
        )

    # ═════════════════════════════════════════════════════════════
    #  ACTIONS
    # ═════════════════════════════════════════════════════════════

    def _set_status(self, text: str, color: str = C_TEXT_DIM):
        """Update status bar (thread-safe)."""
        def _update():
            self.status_label.configure(text=text, text_color=color)
        self.after(0, _update)

    def _set_progress(self, value: float | None = None, label: str | None = None):
        """Update progress bar in indeterminate or determinate mode."""
        def _update():
            if value is None:
                self.progress_bar.stop()
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start()
                if label:
                    self.progress_value_label.configure(text=label)
                return

            progress = max(0.0, min(float(value), 1.0))
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(progress)
            self.progress_value_label.configure(text=f"{int(progress * 100):d}%")
        self.after(0, _update)

    def _on_task_progress(
        self,
        text: str,
        color: str = C_ACCENT,
        progress: float | None = None,
    ):
        """Update status and optional determinate progress from worker threads."""
        self._set_status(text, color)
        self._update_download_waiting_status(text, progress)
        if progress is not None:
            self._set_progress(progress)

    def _save_current_preferences(self) -> None:
        """Persist currently selected transcript preferences."""
        try:
            self.settings.update({
                "selected_language": self.language_var.get(),
                "selected_mode": self.mode_var.get(),
                "selected_whisper_model": self.whisper_model_var.get(),
                "show_timestamps": bool(self.show_timestamps_var.get()),
            })
            self.settings = save_settings(self.settings)
        except Exception as e:
            print(f"Cannot save settings: {e}")

    def _on_close(self):
        """Persist preferences and close the app."""
        self._save_current_preferences()
        try:
            self.destroy()
        except Exception:
            pass

    def _sync_output_actions(self):
        """Keep export actions aligned with whether transcript data is available."""
        if not hasattr(self, "output_action_buttons"):
            return

        state = "normal" if self.current_segments and not self.is_processing else "disabled"
        for button in self.output_action_buttons:
            try:
                button.configure(state=state)
            except Exception:
                pass

    def _set_controls_enabled(self, enabled: bool):
        """Enable/disable controls that should not change while a task is running."""
        state = "normal" if enabled else "disabled"
        controls = [
            self.url_entry,
            *getattr(self, "url_utility_buttons", []),
            self.settings_btn,
            self.language_dropdown,
            self.mode_dropdown,
            self.whisper_model_dropdown,
            self.timestamps_switch,
            self.download_format_dropdown,
            self.video_quality_dropdown,
            self.cookie_browser_dropdown,
            *self.action_buttons,
        ]
        if getattr(self, "prompt_templates", []):
            controls.extend(getattr(self, "prompt_controls", []))

        for control in controls:
            try:
                control.configure(state=state)
            except Exception:
                pass

        if enabled:
            self._on_format_change(self.download_format_var.get())
            self._sync_output_actions()

    def _set_processing(self, active: bool, button: str = "all"):
        """Enable/disable processing state (thread-safe)."""
        def _update():
            self.is_processing = active
            if active:
                self._set_controls_enabled(False)
                if button in ("all", "transcript"):
                    self.get_btn.configure(state="disabled", text="⏳ Đang lấy...")
                if button in ("all", "video"):
                    self.download_video_btn.configure(state="disabled", text="⏳ Đang tải...")
                self.cancel_btn.configure(state="normal", text="⛔ Hủy")
                self.progress_value_label.configure(text="...")
                self.progress_value_label.grid()
                self.progress_bar.grid()
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start()
            else:
                self._set_controls_enabled(True)
                self.get_btn.configure(state="normal", text="⚡ Lấy Transcript")
                self.download_video_btn.configure(state="normal", text="⬇️ Tải Video")
                self.cancel_btn.configure(state="disabled", text="⛔ Hủy")
                self.progress_bar.stop()
                self.progress_bar.set(0)
                self.progress_bar.grid_remove()
                self.progress_value_label.grid_remove()
        self.after(0, _update)

    def _on_cancel_processing(self):
        """Request cancellation for the active background task."""
        if not self.is_processing:
            return
        self.cancel_event.set()
        self.cancel_btn.configure(state="disabled", text="Đang hủy...")
        self._set_status("⛔ Đang hủy tác vụ...", C_ORANGE)

    def _set_output(self, text: str):
        """Set output textbox content (thread-safe)."""
        def _update():
            self.download_wait_active = False
            if self.download_wait_job is not None:
                try:
                    self.after_cancel(self.download_wait_job)
                except Exception:
                    pass
                self.download_wait_job = None
            try:
                self.download_wait_canvas.delete("all")
                self.download_wait_frame.grid_remove()
            except Exception:
                pass

            self._set_output_expanded(True)
            self.output_text.grid()
            self.output_text.tkraise()
            self.output_text.configure(text_color=C_TEXT)
            self.output_text.delete("1.0", "end")
            display_text = text.strip() or "Không có nội dung transcript để hiển thị."
            self.output_text.insert("1.0", display_text)
            try:
                self.output_text.yview_moveto(0)
            except Exception:
                pass
            words = len(display_text.split())
            lines = display_text.count("\n") + 1
            self.word_count_label.configure(text=f"{words:,} từ  •  {lines:,} dòng")
            self.output_state_label.configure(text="Đang hiển thị transcript", text_color=C_ACCENT_2)
            self._sync_output_actions()
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
        self._save_current_preferences()
        self._refresh_output()

    def _on_global_hotkey(self):
        """Handle Ctrl+Shift+C global hotkey to copy and fill URL."""
        if self.is_processing:
            return
            
        if HAS_KEYBOARD:
            try:
                keyboard.send('ctrl+c')
            except Exception:
                pass
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
        self.url_entry.configure(border_color=C_ACCENT)
        self._set_status("✅ URL đã sẵn sàng", C_ACCENT_2)

    def _show_settings(self):
        """Show app settings for Obsidian and Markdown export."""
        settings_win = ctk.CTkToplevel(self)
        settings_win.title("Settings")
        settings_win.geometry("620x540")
        settings_win.resizable(False, False)
        settings_win.attributes("-topmost", True)

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 620) // 2
        y = self.winfo_y() + (self.winfo_height() - 540) // 2
        settings_win.geometry(f"+{x}+{y}")

        settings_win.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(
            settings_win,
            fg_color=C_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=C_BORDER,
        )
        container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        container.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            container,
            text="Obsidian Export",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=C_TEXT,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(16, 12))

        vault_var = ctk.StringVar(value=str(self.settings.get("obsidian_vault_path", "")))
        subfolder_var = ctk.StringVar(value=str(self.settings.get("obsidian_subfolder", "Resources/YouTube")))
        pattern_var = ctk.StringVar(value=str(self.settings.get("filename_pattern", "{date_compact}_{title}")))
        markdown_mode_var = ctk.StringVar(value=str(self.settings.get("markdown_mode", "Clean Transcript")))
        auto_open_var = ctk.BooleanVar(value=bool(self.settings.get("auto_open_after_export", False)))
        include_metadata_var = ctk.BooleanVar(value=bool(self.settings.get("include_metadata", True)))
        include_description_var = ctk.BooleanVar(value=bool(self.settings.get("include_video_description", False)))
        clean_description_var = ctk.BooleanVar(value=bool(self.settings.get("clean_description", True)))
        extract_chapters_var = ctk.BooleanVar(value=bool(self.settings.get("extract_chapters", True)))

        def add_label(text: str, row: int):
            ctk.CTkLabel(
                container,
                text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=C_TEXT_DIM,
            ).grid(row=row, column=0, sticky="w", padx=16, pady=(0, 6))

        add_label("Obsidian Vault Path", 1)
        vault_entry = ctk.CTkEntry(container, textvariable=vault_var, fg_color=C_BG_INPUT)
        vault_entry.grid(row=2, column=0, columnspan=2, sticky="ew", padx=(16, 8), pady=(0, 12))

        def browse_vault():
            selected = filedialog.askdirectory(
                title="Chọn Obsidian vault hoặc folder",
                initialdir=vault_var.get() or str(get_base_dir()),
                parent=settings_win,
            )
            if selected:
                vault_var.set(selected)

        MyCTkButton(
            container,
            text="Browse",
            width=86,
            command=browse_vault,
        ).grid(row=2, column=2, sticky="e", padx=(0, 16), pady=(0, 12))

        add_label("Default subfolder", 3)
        subfolder_entry = ctk.CTkEntry(container, textvariable=subfolder_var, fg_color=C_BG_INPUT)
        subfolder_entry.grid(row=4, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))

        add_label("Filename pattern", 5)
        pattern_entry = ctk.CTkEntry(container, textvariable=pattern_var, fg_color=C_BG_INPUT)
        pattern_entry.grid(row=6, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 4))
        ctk.CTkLabel(
            container,
            text="Placeholders: {date_compact}, {date}, {title}, {video_id}, {channel}, {language}",
            font=ctk.CTkFont(size=11),
            text_color=C_TEXT_DIM,
        ).grid(row=7, column=0, columnspan=3, sticky="w", padx=16, pady=(0, 12))

        add_label("Markdown mode", 8)
        mode_dropdown = MyCTkOptionMenu(
            container,
            variable=markdown_mode_var,
            values=MARKDOWN_MODES,
            fg_color=C_BG_INPUT,
            button_color=C_BORDER,
            button_hover_color=C_ACCENT,
            dropdown_fg_color=C_BG_CARD,
            dropdown_hover_color=C_ACCENT,
        )
        mode_dropdown.grid(row=9, column=0, columnspan=2, sticky="ew", padx=(16, 8), pady=(0, 12))

        auto_open_switch = ctk.CTkSwitch(
            container,
            text="Auto open file after export",
            variable=auto_open_var,
            fg_color=C_BORDER,
            progress_color=C_ACCENT,
            button_color=C_TEXT,
            button_hover_color=C_ACCENT_HOVER,
        )
        auto_open_switch.grid(row=9, column=2, sticky="w", padx=(0, 16), pady=(0, 12))

        add_label("Markdown sections", 10)
        sections_frame = ctk.CTkFrame(container, fg_color="transparent")
        sections_frame.grid(row=11, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))
        sections_frame.columnconfigure(0, weight=1)
        sections_frame.columnconfigure(1, weight=1)

        section_switches = [
            ("Include metadata", include_metadata_var),
            ("Include video description", include_description_var),
            ("Clean description", clean_description_var),
            ("Extract chapters", extract_chapters_var),
        ]
        for index, (label, variable) in enumerate(section_switches):
            switch = ctk.CTkSwitch(
                sections_frame,
                text=label,
                variable=variable,
                fg_color=C_BORDER,
                progress_color=C_ACCENT,
                button_color=C_TEXT,
                button_hover_color=C_ACCENT_HOVER,
            )
            switch.grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 12), pady=3)

        button_row = ctk.CTkFrame(container, fg_color="transparent")
        button_row.grid(row=12, column=0, columnspan=3, sticky="ew", padx=16, pady=(4, 16))
        button_row.columnconfigure(0, weight=1)

        def save_dialog_settings():
            self.settings.update({
                "obsidian_vault_path": vault_var.get().strip(),
                "obsidian_subfolder": subfolder_var.get().strip() or "Resources/YouTube",
                "filename_pattern": pattern_var.get().strip() or "{date_compact}_{title}",
                "markdown_mode": markdown_mode_var.get(),
                "auto_open_after_export": bool(auto_open_var.get()),
                "include_metadata": bool(include_metadata_var.get()),
                "include_video_description": bool(include_description_var.get()),
                "clean_description": bool(clean_description_var.get()),
                "extract_chapters": bool(extract_chapters_var.get()),
            })
            self.settings = save_settings(self.settings)
            self._set_status("✅ Đã lưu settings", C_ACCENT_2)
            settings_win.destroy()

        MyCTkButton(
            button_row,
            text="Save",
            width=110,
            command=save_dialog_settings,
        ).pack(side="right")
        MyCTkButton(
            button_row,
            text="Cancel",
            width=110,
            fg_color=C_BG_ELEVATED,
            hover_color=C_BORDER,
            command=settings_win.destroy,
        ).pack(side="right", padx=(0, 8))

    def _show_about(self):
        """Show About dialog with author info and image."""
        about_win = ctk.CTkToplevel(self)
        about_win.title("About")
        about_win.geometry("400x550")
        about_win.attributes('-topmost', True)
        
        # Center the about window relative to main window
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 550) // 2
        about_win.geometry(f"+{x}+{y}")
        
        # Try to load author.png or author.jpg
        try:
            from PIL import Image
            author_path = get_asset_path("author.png")
            if not author_path.exists():
                author_path = get_asset_path("author.jpg")
                
            if author_path.exists():
                img = Image.open(str(author_path))
                # Resize keeping aspect ratio
                img.thumbnail((250, 250))
                ctk_img = ctk.CTkImage(light_image=img, size=img.size)
                img_lbl = ctk.CTkLabel(about_win, text="", image=ctk_img)
                img_lbl.pack(pady=(30, 10))
        except Exception as e:
            print(f"Cannot load author image: {e}")
            
        # Text
        info_lbl = ctk.CTkLabel(
            about_win,
            text=f"{APP_TITLE} v{APP_VERSION}\n\nTác giả: Phuong\n\nCảm ơn bạn đã sử dụng phần mềm!",
            font=ctk.CTkFont(size=14),
            justify="center",
            text_color=C_TEXT
        )
        info_lbl.pack(pady=20)
        
        close_btn = MyCTkButton(
            about_win, 
            text="Đóng", 
            width=100,
            command=about_win.destroy
        )
        close_btn.pack(pady=10)

    def _show_tutorial(self):
        """Show tutorial dialog with zoomable image."""
        tut_win = ctk.CTkToplevel(self)
        tut_win.title("Hướng dẫn sử dụng")
        tut_win.geometry("880x650")
        tut_win.minsize(640, 420)
        tut_win.attributes('-topmost', True)
        
        # Center the window
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 880) // 2
        y = self.winfo_y() + (self.winfo_height() - 650) // 2
        tut_win.geometry(f"+{x}+{y}")
        
        # Load image
        from PIL import Image, ImageOps, ImageTk
        png_path = get_asset_path("help.png")
        jpg_path = get_asset_path("help.jpg")
        
        valid_path = None
        if png_path.exists():
            valid_path = png_path
        elif jpg_path.exists():
            valid_path = jpg_path
            
        if valid_path:
            try:
                with Image.open(str(valid_path)) as source_img:
                    original_img = ImageOps.exif_transpose(source_img).copy()

                tut_win.grid_columnconfigure(0, weight=1)
                tut_win.grid_rowconfigure(1, weight=1)

                toolbar = ctk.CTkFrame(
                    tut_win,
                    fg_color=C_BG_CARD,
                    corner_radius=10,
                    border_width=1,
                    border_color=C_BORDER,
                )
                toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
                toolbar.grid_columnconfigure(0, weight=1)

                title_label = ctk.CTkLabel(
                    toolbar,
                    text="Ảnh hướng dẫn",
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=C_TEXT,
                )
                title_label.grid(row=0, column=0, sticky="w", padx=12, pady=10)

                zoom_label = ctk.CTkLabel(
                    toolbar,
                    text="100%",
                    width=56,
                    text_color=C_TEXT_DIM,
                )
                zoom_label.grid(row=0, column=1, padx=(8, 4), pady=10)

                viewer = ctk.CTkFrame(
                    tut_win,
                    fg_color=C_BG_INPUT,
                    corner_radius=10,
                    border_width=1,
                    border_color=C_BORDER,
                )
                viewer.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
                viewer.grid_columnconfigure(0, weight=1)
                viewer.grid_rowconfigure(0, weight=1)

                canvas = tk.Canvas(
                    viewer,
                    bg=C_BG_INPUT,
                    highlightthickness=0,
                    bd=0,
                    xscrollincrement=20,
                    yscrollincrement=20,
                )
                v_scroll = ctk.CTkScrollbar(viewer, orientation="vertical", command=canvas.yview)
                h_scroll = ctk.CTkScrollbar(viewer, orientation="horizontal", command=canvas.xview)
                canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

                canvas.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
                v_scroll.grid(row=0, column=1, sticky="ns", padx=(4, 8), pady=(8, 0))
                h_scroll.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(4, 8))

                state = {
                    "scale": 1.0,
                    "photo": None,
                    "user_zoomed": False,
                    "dragging": False,
                }
                tut_win._tutorial_image_state = state

                resample = (
                    Image.Resampling.LANCZOS
                    if hasattr(Image, "Resampling")
                    else Image.LANCZOS
                )

                def render_image():
                    scale = state["scale"]
                    width = max(1, int(original_img.width * scale))
                    height = max(1, int(original_img.height * scale))
                    display_img = original_img.resize((width, height), resample)

                    state["photo"] = ImageTk.PhotoImage(display_img)
                    canvas.delete("tutorial_image")

                    canvas_width = max(canvas.winfo_width(), 1)
                    canvas_height = max(canvas.winfo_height(), 1)
                    image_x = max((canvas_width - width) // 2, 0)
                    image_y = max((canvas_height - height) // 2, 0)

                    canvas.create_image(
                        image_x,
                        image_y,
                        anchor="nw",
                        image=state["photo"],
                        tags="tutorial_image",
                    )
                    canvas.configure(
                        scrollregion=(
                            0,
                            0,
                            max(width + image_x, canvas_width),
                            max(height + image_y, canvas_height),
                        )
                    )
                    zoom_label.configure(text=f"{int(scale * 100)}%")

                def get_fit_scale():
                    canvas.update_idletasks()
                    canvas_width = max(canvas.winfo_width() - 16, 1)
                    canvas_height = max(canvas.winfo_height() - 16, 1)
                    return max(
                        0.1,
                        min(
                            canvas_width / original_img.width,
                            canvas_height / original_img.height,
                            1.0,
                        ),
                    )

                def set_zoom(scale: float, user_zoomed: bool = True):
                    state["scale"] = max(0.1, min(scale, 5.0))
                    state["user_zoomed"] = user_zoomed
                    render_image()

                def zoom_in():
                    set_zoom(state["scale"] * 1.25)

                def zoom_out():
                    set_zoom(state["scale"] / 1.25)

                def zoom_actual():
                    set_zoom(1.0)

                def zoom_fit():
                    set_zoom(get_fit_scale(), user_zoomed=False)

                def on_mousewheel(event):
                    delta = getattr(event, "delta", 0)
                    button = getattr(event, "num", None)

                    if button == 4:
                        delta = 120
                    elif button == 5:
                        delta = -120

                    if delta > 0:
                        zoom_in()
                    elif delta < 0:
                        zoom_out()
                    return "break"

                def start_pan(event):
                    state["dragging"] = True
                    canvas.scan_mark(event.x, event.y)
                    canvas.configure(cursor="fleur")
                    return "break"

                def drag_pan(event):
                    if state["dragging"]:
                        canvas.scan_dragto(event.x, event.y, gain=1)
                    return "break"

                def end_pan(_event):
                    state["dragging"] = False
                    canvas.configure(cursor="")
                    return "break"

                def on_resize(_event):
                    if not state["user_zoomed"]:
                        state["scale"] = get_fit_scale()
                    render_image()

                zoom_out_btn = MyCTkButton(
                    toolbar,
                    text="-",
                    width=36,
                    command=zoom_out,
                )
                zoom_out_btn.grid(row=0, column=2, padx=4, pady=10)

                zoom_in_btn = MyCTkButton(
                    toolbar,
                    text="+",
                    width=36,
                    command=zoom_in,
                )
                zoom_in_btn.grid(row=0, column=3, padx=4, pady=10)

                actual_btn = MyCTkButton(
                    toolbar,
                    text="100%",
                    width=64,
                    command=zoom_actual,
                )
                actual_btn.grid(row=0, column=4, padx=4, pady=10)

                fit_btn = MyCTkButton(
                    toolbar,
                    text="Fit",
                    width=64,
                    command=zoom_fit,
                )
                fit_btn.grid(row=0, column=5, padx=(4, 12), pady=10)

                def bind_mousewheel(_event=None):
                    canvas.focus_set()
                    canvas.bind_all("<MouseWheel>", on_mousewheel)
                    canvas.bind_all("<Button-4>", on_mousewheel)
                    canvas.bind_all("<Button-5>", on_mousewheel)

                def unbind_mousewheel(_event=None):
                    canvas.unbind_all("<MouseWheel>")
                    canvas.unbind_all("<Button-4>")
                    canvas.unbind_all("<Button-5>")

                def close_tutorial():
                    unbind_mousewheel()
                    tut_win.destroy()

                canvas.bind("<Enter>", bind_mousewheel)
                canvas.bind("<Leave>", unbind_mousewheel)
                canvas.bind("<ButtonPress-2>", start_pan)
                canvas.bind("<B2-Motion>", drag_pan)
                canvas.bind("<ButtonRelease-2>", end_pan)
                canvas.bind("<Configure>", on_resize)
                tut_win.protocol("WM_DELETE_WINDOW", close_tutorial)
                tut_win.after(100, zoom_fit)
            except Exception as e:
                print(f"Failed to load {valid_path}: {e}")
                ctk.CTkLabel(tut_win, text=f"Lỗi tải ảnh: {e}", text_color=C_TEXT).pack(expand=True)
        else:
            lbl = ctk.CTkLabel(
                tut_win, 
                text="Chưa có hình ảnh hướng dẫn.\n\nVui lòng lưu ảnh hướng dẫn vào thư mục cài đặt\nvới tên 'help.png' hoặc 'help.jpg'.",
                font=ctk.CTkFont(size=14),
                text_color=C_TEXT
            )
            lbl.pack(expand=True)

    def _mark_url_attention(self, color: str = C_RED):
        """Briefly highlight the URL field when input needs attention."""
        try:
            self.url_entry.configure(border_color=color)
            self.url_entry.focus_set()
            self.after(1200, lambda: self.url_entry.configure(border_color=C_BORDER))
        except Exception:
            pass

    def _on_paste_url(self):
        """Paste clipboard text into the URL field."""
        if self.is_processing:
            return

        try:
            text = pyperclip.paste().strip()
        except Exception:
            try:
                text = self.clipboard_get().strip()
            except Exception:
                text = ""

        if not text:
            self._mark_url_attention(C_ORANGE)
            self._set_status("⚠️ Clipboard đang trống", C_ORANGE)
            return

        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, text)
        self.url_entry.focus_set()

        try:
            extract_video_id(text)
            self.url_entry.configure(border_color=C_ACCENT)
            self._set_status("✅ URL đã sẵn sàng", C_ACCENT_2)
        except ValueError:
            self._mark_url_attention(C_ORANGE)
            self._set_status("⚠️ Clipboard không giống YouTube URL", C_ORANGE)

    def _on_clear_url(self):
        """Clear the URL field and return focus to it."""
        if self.is_processing:
            return
        self.url_entry.delete(0, "end")
        self.url_entry.configure(border_color=C_BORDER)
        self.url_entry.focus_set()
        self._set_status("✅ Sẵn sàng — dán YouTube URL để bắt đầu", C_ACCENT_2)

    def _on_get_transcript(self):
        """Handle Get Transcript button click."""
        if self.is_processing:
            return

        url = self.url_entry.get().strip()
        if not url:
            self._mark_url_attention(C_ORANGE)
            self._set_status("⚠️ Vui lòng nhập YouTube URL", C_ORANGE)
            return

        try:
            video_id = extract_video_id(url)
        except ValueError as e:
            self._mark_url_attention()
            self._set_status(f"❌ {str(e).split(chr(10))[0]}", C_RED)
            messagebox.showerror("URL không hợp lệ", str(e))
            return

        mode = self.mode_var.get()
        language = self.language_var.get().lower()
        if language == "auto":
            language = "auto"

        self.cancel_event.clear()
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
            self._mark_url_attention(C_ORANGE)
            self._set_status("⚠️ Vui lòng nhập YouTube URL", C_ORANGE)
            return

        try:
            video_id = extract_video_id(url)
        except ValueError as e:
            self._mark_url_attention()
            self._set_status(f"❌ {str(e).split(chr(10))[0]}", C_RED)
            messagebox.showerror("URL không hợp lệ", str(e))
            return

        self.cancel_event.clear()
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
        cookie_browser = self.cookie_browser_var.get()
        wait_title = f"Đang tải {format_type} • {quality if format_type != 'Audio (M4A)' else 'audio'}"
        
        try:
            self._show_download_waiting(wait_title)
            self._set_status("⬇️ Đang khởi tạo tải xuống...", C_ACCENT)
            
            file_path, title = download_video(
                url,
                format_type=format_type,
                quality=quality,
                cookie_browser=cookie_browser,
                cancel_event=self.cancel_event,
                progress_callback=lambda msg, progress=None: self._on_task_progress(
                    f"⬇️ {msg}",
                    C_ACCENT,
                    progress,
                )
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
            
        except VideoDownloadCancelledError:
            self._set_status("⛔ Đã hủy tải file", C_ORANGE)
        except VideoDownloadError as e:
            self._set_status("❌ Lỗi tải file", C_RED)
            self.after(0, lambda: messagebox.showerror("Lỗi Tải Xuống", str(e)))
        except Exception as e:
            self._set_status(f"❌ Lỗi: {str(e)[:80]}", C_RED)
            self.after(0, lambda: messagebox.showerror("Lỗi", str(e)))
        finally:
            self._hide_download_waiting()
            self._set_processing(False)

    def _process_transcript(self, url: str, video_id: str, mode: str, language: str):
        """Process transcript fetching (background thread)."""
        self._set_processing(True, button="transcript")
        self._show_output_loading(
            "Đang lấy transcript",
            "Nội dung transcript sẽ hiện ở đây ngay khi lấy xong.",
        )

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
                    "channel": "",
                }

                show_ts = self.show_timestamps_var.get()
                formatted = format_transcript_text(segments, include_timestamps=show_ts)
                self._set_output(formatted)
                self._set_status(
                    f"✅ Đã hiển thị {len(segments)} segments — đang lấy metadata video...",
                    C_ACCENT_2,
                )

                try:
                    video_metadata = get_youtube_metadata(url)
                    if video_metadata.get("id"):
                        self.current_metadata["id"] = video_metadata["id"]
                        self.current_metadata["video_id"] = video_metadata["id"]
                    if video_metadata.get("title") and video_metadata["title"] != "Unknown":
                        self.current_metadata["title"] = video_metadata["title"]
                    for key in (
                        "description",
                        "channel",
                        "channel_id",
                        "uploader",
                        "upload_date",
                        "duration",
                        "thumbnail",
                        "webpage_url",
                        "tags",
                        "categories",
                    ):
                        self.current_metadata[key] = video_metadata.get(key, self.current_metadata.get(key, ""))

                    description = self.current_metadata.get("description", "")
                    self.current_metadata["clean_description_text"] = clean_youtube_description(description)
                    self.current_metadata["chapters"] = extract_chapters_from_description(description)
                except Exception:
                    pass

                self._set_status(
                    f"🎉 Hoàn tất! {len(segments)} segments — {used_mode}",
                    C_ACCENT_2,
                )
            else:
                self._set_output("")
                self._set_status("⚠️ Không có nội dung transcript để hiển thị", C_ORANGE)

        except TranscriptNotFoundError as e:
            self._set_status(f"❌ {str(e).split(chr(10))[0]}", C_RED)
            self.after(0, lambda: messagebox.showwarning("Không có Transcript", str(e)))
        except AudioDownloadCancelledError:
            self._set_status("⛔ Đã hủy tải audio", C_ORANGE)
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
            cookie_browser=self.cookie_browser_var.get(),
            cancel_event=self.cancel_event,
            progress_callback=lambda msg, progress=None: self._on_task_progress(
                f"⬇️ {msg}",
                C_ACCENT,
                progress,
            ),
        )

        if self.cancel_event.is_set():
            raise AudioDownloadCancelledError("Đã hủy tải audio.")

        self.current_metadata = self.current_metadata or {}
        self.current_metadata["title"] = title

        self._set_status("🎤 Đang chạy Speech-to-Text...", C_PURPLE)
        self._set_progress(None, "STT")
        model_size = self.whisper_model_var.get()
        whisper_lang = None if language == "auto" else language

        segments = transcribe_audio(
            audio_path,
            model_size=model_size,
            language=whisper_lang,
            progress_callback=lambda msg: self._set_status(f"🎤 {msg}", C_PURPLE),
        )

        return segments

    def _get_selected_prompt_template_id(self) -> str | None:
        """Return the selected prompt template id from the display name."""
        template_var = getattr(self, "prompt_template_var", None)
        template_name = template_var.get() if template_var else ""
        return getattr(self, "prompt_template_name_to_id", {}).get(template_name)

    def _on_prompt_template_selected(self):
        """Refresh the template description when the user chooses a prompt type."""
        template_id = self._get_selected_prompt_template_id()
        if not template_id:
            self.prompt_description_label.configure(text="")
            return

        try:
            template = get_template(template_id)
            self.prompt_description_label.configure(text=template.get("description", ""))
        except Exception as e:
            self.prompt_description_label.configure(text="Cannot load this template.")
            self._set_status(f"Prompt template error: {e}", C_ORANGE)

    def _format_prompt_chapters(self) -> str:
        """Format metadata chapters for prompt context."""
        metadata = self.current_metadata or {}
        chapters = metadata.get("chapters")
        if chapters is None:
            chapters = extract_chapters_from_description(metadata.get("description", ""))
        if not chapters:
            return ""

        lines = []
        for chapter in chapters:
            if isinstance(chapter, dict):
                timestamp = str(chapter.get("timestamp", "") or "").strip()
                title = str(chapter.get("title", "") or "").strip()
                line = f"{timestamp} {title}".strip()
                if line:
                    lines.append(f"- {line}")
            else:
                text = str(chapter).strip()
                if text:
                    lines.append(f"- {text}")
        return "\n".join(lines)

    def _get_prompt_url(self) -> str:
        metadata = self.current_metadata or {}
        url = metadata.get("webpage_url") or metadata.get("url") or ""
        if url:
            return str(url)
        try:
            return self.url_entry.get().strip()
        except Exception:
            return ""

    def _get_prompt_transcript_text(self) -> str:
        """Return transcript text using the selected prompt transcript mode."""
        if not self.current_segments:
            return ""

        mode = self.prompt_transcript_mode_var.get().lower()
        if "timestamp" in mode:
            return format_transcript_text(self.current_segments, include_timestamps=True)
        if "raw" in mode:
            return format_transcript_text(self.current_segments, include_timestamps=False)
        return format_clean_transcript_text(self.current_segments, include_timestamps=False)

    def _build_prompt_context(self, include_transcript: bool) -> dict:
        """Build template variables from the current video metadata and transcript."""
        metadata = self.current_metadata or {}
        url = self._get_prompt_url()
        description = metadata.get("clean_description_text")
        if not description:
            description = clean_youtube_description(metadata.get("description", ""))

        title = str(metadata.get("title", "") or "").strip()
        if not title and url:
            video_id = extract_video_id(url)
            title = f"YouTube Video {video_id}" if video_id else "YouTube Video"

        return {
            "VIDEO_TITLE": title,
            "VIDEO_URL": url,
            "CHANNEL_NAME": metadata.get("channel") or metadata.get("uploader") or "",
            "DESCRIPTION": description or "",
            "CHAPTERS": self._format_prompt_chapters(),
            "TRANSCRIPT": self._get_prompt_transcript_text() if include_transcript else "",
        }

    def _set_prompt_preview(self, text: str) -> None:
        if not hasattr(self, "prompt_preview_text"):
            return
        self.prompt_preview_text.delete("1.0", "end")
        self.prompt_preview_text.insert("1.0", text)
        self.prompt_preview_text.see("1.0")

    def _render_selected_prompt(self, include_transcript: bool) -> str:
        template_id = self._get_selected_prompt_template_id()
        if not template_id:
            self._set_status("No prompt template selected.", C_ORANGE)
            return ""

        try:
            context = self._build_prompt_context(include_transcript=include_transcript)
            prompt = render_prompt(template_id, context, include_transcript=include_transcript)
        except Exception as e:
            self._set_status(f"Cannot render prompt: {e}", C_RED)
            return ""

        self._set_prompt_preview(prompt)
        return prompt

    def _copy_text_to_clipboard(self, text: str) -> None:
        try:
            pyperclip.copy(text)
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()

    def _on_generate_prompt(self):
        """Render a prompt preview, using transcript text when available."""
        prompt = self._render_selected_prompt(include_transcript=bool(self.current_segments))
        if not prompt:
            return
        if self.current_segments:
            self._set_status("Prompt generated with current transcript.", C_ACCENT_2)
        else:
            self._set_status("Prompt generated. Fetch transcript to insert transcript content.", C_ORANGE)

    def _on_copy_prompt_only(self):
        """Copy the rendered prompt while keeping the transcript placeholder."""
        prompt = self._render_selected_prompt(include_transcript=False)
        if not prompt:
            return
        self._copy_text_to_clipboard(prompt)
        self._set_status("Prompt copied. {TRANSCRIPT} placeholder kept.", C_ACCENT_2)

    def _on_copy_prompt_with_transcript(self):
        """Copy the rendered prompt with the current transcript inserted."""
        if not self.current_segments:
            self._set_status("No transcript available for prompt copy.", C_ORANGE)
            return
        prompt = self._render_selected_prompt(include_transcript=True)
        if not prompt:
            return
        self._copy_text_to_clipboard(prompt)
        self._set_status("Prompt and transcript copied to clipboard.", C_ACCENT_2)

    def _on_copy(self):
        """Copy transcript to clipboard."""
        text = self.output_text.get("1.0", "end").strip()
        if not text or text.startswith("Chưa có transcript"):
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

    def _build_export_metadata(self, ext: str) -> dict:
        metadata = dict(self.current_metadata or {})
        if ext == "md":
            metadata["markdown_mode"] = self.settings.get("markdown_mode", "Clean Transcript")
            metadata["include_timestamps"] = bool(self.show_timestamps_var.get())
            metadata["include_metadata"] = bool(self.settings.get("include_metadata", True))
            metadata["include_video_description"] = bool(self.settings.get("include_video_description", False))
            metadata["clean_description"] = bool(self.settings.get("clean_description", True))
            metadata["extract_chapters"] = bool(self.settings.get("extract_chapters", True))
        return metadata

    @staticmethod
    def _slug_filename_part(value: str) -> str:
        """Create a compact filename token while preserving readable Unicode text."""
        safe = sanitize_filename(value)
        safe = re.sub(r"\s+", "-", safe)
        safe = re.sub(r"-{2,}", "-", safe)
        return safe.strip("-_. ") or "untitled"

    def _build_export_filename(self, ext: str, metadata: dict) -> str:
        date_value = str(metadata.get("date", get_current_date()) or get_current_date())
        values = {
            "date": date_value,
            "date_compact": re.sub(r"\D", "", date_value) or get_current_date().replace("-", ""),
            "title": metadata.get("title", "transcript"),
            "video_id": metadata.get("video_id", ""),
            "channel": metadata.get("channel", ""),
            "language": metadata.get("language", ""),
        }
        pattern = self.settings.get("filename_pattern", "{date_compact}_{title}") if ext == "md" else "{title}"

        if ext == "md":
            values = {key: self._slug_filename_part(str(value)) for key, value in values.items()}
        else:
            values = {key: str(value) for key, value in values.items()}

        try:
            filename = pattern.format_map(values)
        except (KeyError, ValueError):
            filename = f"{values['date_compact']}_{values['title']}" if ext == "md" else values["title"]

        return f"{sanitize_filename(filename)}.{ext}"

    def _get_initial_export_dir(self) -> Path:
        last_dir = self.settings.get("last_export_dir", "")
        if last_dir:
            path = Path(last_dir)
            if path.exists():
                return path
        return get_base_dir() / "exports"

    def _get_obsidian_export_dir(self) -> Path | None:
        vault = str(self.settings.get("obsidian_vault_path", "")).strip()
        if not vault:
            selected = filedialog.askdirectory(
                title="Chọn Obsidian vault hoặc folder lưu Markdown",
                initialdir=str(self._get_initial_export_dir()),
            )
            if not selected:
                return None
            vault = selected
            self.settings["obsidian_vault_path"] = selected
            try:
                self.settings = save_settings(self.settings)
            except Exception:
                pass

        vault_path = Path(vault)
        if not vault_path.exists():
            selected = filedialog.askdirectory(
                title="Vault path không tồn tại. Chọn lại folder lưu Markdown",
                initialdir=str(self._get_initial_export_dir()),
            )
            if not selected:
                return None
            vault_path = Path(selected)
            self.settings["obsidian_vault_path"] = selected
            try:
                self.settings = save_settings(self.settings)
            except Exception:
                pass

        subfolder = str(self.settings.get("obsidian_subfolder", "")).strip().strip("/\\")
        return vault_path / subfolder if subfolder else vault_path

    def _unique_export_path(self, path: Path) -> Path:
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        index = 2
        while True:
            candidate = parent / f"{stem}_{index}{suffix}"
            if not candidate.exists():
                return candidate
            index += 1

    def _remember_export_dir(self, file_path: str) -> None:
        self.settings["last_export_dir"] = str(Path(file_path).parent)
        try:
            self.settings = save_settings(self.settings)
        except Exception:
            pass

    def _open_exported_file(self, file_path: str) -> None:
        if not self.settings.get("auto_open_after_export", False):
            return
        try:
            os.startfile(file_path)
        except Exception as e:
            print(f"Cannot open exported file: {e}")

    def _save_file(self, ext: str, export_func):
        """Generic save file handler."""
        if not self.current_segments:
            self._set_status("⚠️ Không có transcript để lưu", C_ORANGE)
            return

        metadata = self._build_export_metadata(ext)
        default_name = self._build_export_filename(ext, metadata)

        type_names = {
            "txt": "Text Files",
            "md": "Markdown Files",
            "srt": "SRT Subtitle Files",
        }

        file_path = None
        if ext == "md":
            obsidian_dir = self._get_obsidian_export_dir()
            if obsidian_dir:
                file_path = str(self._unique_export_path(obsidian_dir / default_name))

        if not file_path:
            file_path = filedialog.asksaveasfilename(
                defaultextension=f".{ext}",
                initialdir=str(self._get_initial_export_dir()),
                initialfile=default_name,
                filetypes=[(type_names.get(ext, "Files"), f"*.{ext}"), ("All Files", "*.*")],
                title=f"Save as .{ext.upper()}",
            )

        if not file_path:
            return

        try:
            export_func(self.current_segments, file_path, metadata)
            self._remember_export_dir(file_path)
            self._set_status(f"💾 Đã lưu: {Path(file_path).name}", C_ACCENT_2)
            self._open_exported_file(file_path)
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
        if hasattr(self, "prompt_preview_text"):
            self._set_prompt_preview("")
        self._set_status("✅ Sẵn sàng — dán YouTube URL để bắt đầu", C_ACCENT_2)

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

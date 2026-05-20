"""
YouTube Knowledge Clipper — Main Application
Desktop app for extracting YouTube transcripts and speech-to-text.
Built with CustomTkinter for a modern dark UI.
"""

import os
import sys
import threading
import time
import math
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
    get_video_info,
)
from video_service import download_video, VideoDownloadCancelledError, VideoDownloadError
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
COOKIE_BROWSERS = ["Auto", "None", "Edge", "Chrome", "Firefox", "Brave", "Vivaldi", "Opera"]

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

        # Hide the main window until the welcome loading animation completes.
        self.withdraw()
        self.after(80, self._show_welcome_effect)

    def _show_main_window(self):
        """Reveal and focus the main window after startup loading."""
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _show_welcome_effect(self):
        """Show a short non-blocking welcome splash when the app starts."""
        if getattr(self, "_welcome_splash", None):
            try:
                if self._welcome_splash.winfo_exists():
                    return
            except Exception:
                pass

        splash = ctk.CTkToplevel(self)
        self._welcome_splash = splash
        splash.overrideredirect(True)
        splash.configure(fg_color=C_BG_DARK)

        try:
            splash.attributes("-alpha", 0.0)
            splash.attributes("-topmost", True)
        except Exception:
            pass

        splash_width = 620
        splash_height = 320
        self.update_idletasks()
        x = (self.winfo_screenwidth() - splash_width) // 2
        y = (self.winfo_screenheight() - splash_height) // 2
        splash.geometry(f"{splash_width}x{splash_height}+{x}+{y}")
        splash.lift()

        card = ctk.CTkFrame(
            splash,
            fg_color=C_BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=C_BORDER,
        )
        card.pack(fill="both", expand=True, padx=14, pady=14)
        card.grid_columnconfigure(0, minsize=188)
        card.grid_columnconfigure(1, weight=1)

        visual_canvas = tk.Canvas(
            card,
            width=168,
            height=152,
            bg=C_BG_CARD,
            highlightthickness=0,
            bd=0,
        )
        visual_canvas.grid(row=0, column=0, rowspan=3, padx=(24, 18), pady=(34, 0), sticky="n")

        title_label = ctk.CTkLabel(
            card,
            text=APP_TITLE,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=C_TEXT,
            anchor="w",
        )
        title_label.grid(row=0, column=1, sticky="ew", padx=(0, 34), pady=(44, 0))

        subtitle_label = ctk.CTkLabel(
            card,
            text="Sẵn sàng trích xuất transcript, tải video và chạy STT",
            font=ctk.CTkFont(size=13),
            text_color=C_TEXT_DIM,
            anchor="w",
            wraplength=340,
        )
        subtitle_label.grid(row=1, column=1, sticky="ew", padx=(0, 34), pady=(6, 0))

        badge_label = ctk.CTkLabel(
            card,
            text="Transcript • Download • Whisper",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_ACCENT,
            anchor="w",
        )
        badge_label.grid(row=2, column=1, sticky="ew", padx=(0, 34), pady=(18, 0))

        progress = ctk.CTkProgressBar(
            card,
            mode="determinate",
            height=6,
            progress_color=C_ACCENT,
            fg_color=C_BG_INPUT,
            corner_radius=3,
        )
        progress.grid(row=3, column=0, columnspan=2, sticky="ew", padx=34, pady=(30, 8))
        progress.set(0)

        hint_label = ctk.CTkLabel(
            card,
            text="Click hoặc Esc để bỏ qua",
            font=ctk.CTkFont(size=10),
            text_color=C_TEXT_DIM,
        )
        hint_label.grid(row=4, column=0, columnspan=2, sticky="ew", padx=34, pady=(0, 22))

        closed = {"value": False}

        def draw_welcome_visual(step: int):
            visual_canvas.delete("all")
            width = 168
            height = 152
            center_x = width / 2
            center_y = height / 2 + 2
            scale = 1.42
            pulse = (math.sin(step * 0.36) + 1) / 2
            tilt = math.sin(step * 0.16) * 5 * scale
            yaw = math.sin(step * 0.2) * 7 * scale

            def sx(value: float) -> float:
                return center_x + (value - 52) * scale

            def sy(value: float) -> float:
                return center_y + (value - 52) * scale

            # Hologram base rings.
            visual_canvas.create_oval(
                sx(14),
                sy(78),
                sx(90),
                sy(95),
                outline="#263247",
                width=2,
            )
            visual_canvas.create_oval(
                sx(23),
                sy(82),
                sx(81),
                sy(91),
                outline="#1f6feb",
                width=1,
            )
            visual_canvas.create_arc(
                sx(10),
                sy(74),
                sx(94),
                sy(98),
                start=(step * 10) % 360,
                extent=72,
                outline=C_ACCENT_2,
                width=2,
                style="arc",
            )

            # Hologram scan lines.
            for offset in range(0, 58, 9):
                y = 26 + offset + math.sin(step * 0.2 + offset) * 1.4
                visual_canvas.create_line(
                    sx(24),
                    sy(y),
                    sx(80),
                    sy(y),
                    fill="#1f6feb",
                    width=1,
                )

            # A pseudo-3D rounded play slab, drawn as layered polygons.
            front = [
                (sx(28) + yaw, sy(30) + tilt),
                (sx(72) + yaw, sy(24) - tilt * 0.2),
                (sx(82) - yaw * 0.3, sy(51)),
                (sx(70) - yaw, sy(72) + tilt * 0.2),
                (sx(29) - yaw * 0.2, sy(66) - tilt),
                (sx(20) + yaw * 0.2, sy(48)),
            ]
            back = [(x + 10, y + 10) for x, y in front]

            for index in range(len(front)):
                next_index = (index + 1) % len(front)
                side = [
                    front[index],
                    front[next_index],
                    back[next_index],
                    back[index],
                ]
                visual_canvas.create_polygon(side, fill="#11223a", outline="#1f6feb")

            glow_color = C_PURPLE if pulse > 0.62 else C_ACCENT
            visual_canvas.create_polygon(back, fill="#07111f", outline="#1f6feb", width=1)
            visual_canvas.create_polygon(front, fill="#10243b", outline="#0a1320", width=5)
            visual_canvas.create_polygon(front, fill="#10243b", outline=glow_color, width=2)

            play_depth = 7 + pulse * 4
            play_shadow = [
                (sx(43) + yaw * 0.25 + play_depth, sy(38) + play_depth),
                (sx(43) + yaw * 0.25 + play_depth, sy(60) + play_depth),
                (sx(62) + yaw * 0.25 + play_depth, sy(49) + play_depth),
            ]
            play_front = [
                (sx(43) + yaw * 0.25, sy(38)),
                (sx(43) + yaw * 0.25, sy(60)),
                (sx(62) + yaw * 0.25, sy(49)),
            ]
            visual_canvas.create_polygon(play_shadow, fill="#07111f", outline="")
            visual_canvas.create_polygon(play_front, fill=C_ACCENT_2, outline="#b6f7c4", width=1)

            # Orbiting hologram particles.
            for i in range(5):
                theta = step * 0.22 + (i * math.tau / 5)
                ox = center_x + math.cos(theta) * 58
                oy = center_y + math.sin(theta) * 27 + 12
                radius = 2.2 + (i % 2) * 1.0
                color = C_ACCENT_2 if i % 2 else C_ACCENT
                visual_canvas.create_oval(ox - radius, oy - radius, ox + radius, oy + radius, fill=color, outline="")

            for i, label in enumerate(("YT", "AI")):
                theta = -step * 0.18 + (i * math.pi)
                ox = center_x + math.cos(theta) * 50
                oy = center_y + math.sin(theta) * 16 + 54
                visual_canvas.create_rectangle(
                    ox - 15,
                    oy - 8,
                    ox + 15,
                    oy + 8,
                    fill=C_BG_INPUT,
                    outline=C_BORDER,
                    width=1,
                )
                visual_canvas.create_text(
                    ox,
                    oy,
                    text=label,
                    fill=C_TEXT_DIM,
                    font=("Segoe UI", 8, "bold"),
                )

            visual_canvas.create_text(
                center_x,
                18,
                text="PLAY",
                fill=C_ACCENT,
                font=("Segoe UI", 11, "bold"),
            )

        def close_splash(_event=None):
            if closed["value"]:
                return
            closed["value"] = True
            try:
                splash.destroy()
            except Exception:
                pass
            self._welcome_splash = None
            self._show_main_window()

        def animate(step: int = 0):
            if closed["value"]:
                return
            try:
                if not splash.winfo_exists():
                    return

                total_steps = 34
                fade_in_steps = 8
                fade_out_start = 26

                if step <= fade_in_steps:
                    alpha = 0.12 + (step / fade_in_steps) * 0.84
                elif step >= fade_out_start:
                    alpha = max(0.0, 0.96 - ((step - fade_out_start) / 8) * 0.96)
                else:
                    alpha = 0.96

                try:
                    splash.attributes("-alpha", alpha)
                except Exception:
                    pass

                draw_welcome_visual(step)
                progress.set(min(step / total_steps, 1.0))
                if step >= total_steps:
                    close_splash()
                else:
                    splash.after(45, lambda: animate(step + 1))
            except Exception:
                close_splash()

        splash.bind("<Escape>", close_splash)
        splash.bind("<Button-1>", close_splash)
        card.bind("<Button-1>", close_splash)
        animate()


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

        # About button
        self.about_btn = ctk.CTkButton(
            header_frame,
            text="ℹ️ About",
            width=70,
            height=28,
            fg_color="transparent",
            hover_color=C_BORDER,
            text_color=C_TEXT_DIM,
            command=self._show_about
        )
        self.about_btn.pack(side="right")

        # Tutorial button
        self.tutorial_btn = ctk.CTkButton(
            header_frame,
            text="📖 Hướng dẫn",
            width=90,
            height=28,
            fg_color="transparent",
            hover_color=C_BORDER,
            text_color=C_TEXT_DIM,
            command=self._show_tutorial
        )
        self.tutorial_btn.pack(side="right", padx=(0, 5))

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
        url_label.grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(12, 4))

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
        hint_label.grid(row=2, column=0, columnspan=4, sticky="w", padx=16, pady=(0, 10))

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
        self.download_video_btn.grid(row=1, column=2, sticky="e", padx=(0, 8), pady=(0, 4))

        self.cancel_btn = ctk.CTkButton(
            self.input_card,
            text="⛔ Hủy",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=42,
            width=110,
            fg_color=C_RED,
            hover_color=self._lighten_color(C_RED),
            corner_radius=10,
            state="disabled",
            command=self._on_cancel_processing,
        )
        self.cancel_btn.grid(row=1, column=3, sticky="e", padx=(0, 16), pady=(0, 4))

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
        self.video_quality_var = ctk.StringVar(value="480p")
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

        # ── Row 2-3: Browser Cookies
        self._make_option_label(self.options_card, "🍪 Browser Cookies", 2, 2)
        self.cookie_browser_var = ctk.StringVar(value="Auto")
        self.cookie_browser_dropdown = ctk.CTkOptionMenu(
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
        self.cookie_browser_dropdown.grid(row=3, column=2, padx=16, pady=(0, 16), sticky="w")

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

        self.download_wait_frame = ctk.CTkFrame(
            self.output_card,
            fg_color=C_BG_INPUT,
            corner_radius=8,
            border_width=0,
        )
        self.download_wait_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
        self.download_wait_frame.grid_columnconfigure(0, weight=1)
        self.download_wait_frame.grid_rowconfigure(1, weight=1)
        self.download_wait_frame.grid_remove()

        self.download_wait_title = ctk.CTkLabel(
            self.download_wait_frame,
            text="Đang chuẩn bị tải video",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=C_TEXT,
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
        )
        self.download_wait_status.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 16))

        self.download_wait_active = False
        self.download_wait_step = 0
        self.download_wait_job = None

        # Placeholder
        self._show_placeholder()

    def _show_placeholder(self):
        """Show placeholder text."""
        self._hide_download_waiting()
        self.output_text.configure(text_color=C_TEXT_DIM)
        self.output_text.delete("1.0", "end")
        placeholder = (
            "Chào bạn! Mình là YouTube Knowledge Clipper\n\n"
            "Bước 1: 🔗 Paste YouTube URL\n"
            "Bước 2: ⚙️ Chọn options\n"
            "Bước 3: ⚡ Bấm \"Get Transcript\"\n"
        )
        self.output_text.insert("1.0", placeholder)

    def _show_download_waiting(self, title: str = "Đang tải video") -> None:
        """Show a lightweight waiting animation while yt-dlp is downloading."""
        def _update():
            self.download_wait_title.configure(text=title)
            self.download_wait_status.configure(text="Đang kết nối YouTube...")
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

        # Top label.
        canvas.create_text(
            center_x,
            max(24, center_y - ring_ry - 20),
            text="Neon Download Portal",
            fill=C_TEXT,
            font=("Segoe UI", 14, "bold"),
        )
        canvas.create_text(
            center_x,
            max(45, center_y - ring_ry + 2),
            text="pulling video streams into your library",
            fill=C_TEXT_DIM,
            font=("Segoe UI", 10),
        )

        self.download_wait_step += 1
        self.download_wait_job = self.after(36, self._animate_download_waiting)

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
            wraplength=600,
        )
        self.status_label.pack(side="left", padx=16, pady=6)

        self.progress_value_label = ctk.CTkLabel(
            self.status_frame,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C_TEXT_DIM,
            width=48,
        )

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

    def _set_controls_enabled(self, enabled: bool):
        """Enable/disable controls that should not change while a task is running."""
        state = "normal" if enabled else "disabled"
        controls = [
            self.url_entry,
            self.language_dropdown,
            self.mode_dropdown,
            self.whisper_model_dropdown,
            self.timestamps_switch,
            self.download_format_dropdown,
            self.video_quality_dropdown,
            self.cookie_browser_dropdown,
            *self.action_buttons,
        ]

        for control in controls:
            try:
                control.configure(state=state)
            except Exception:
                pass

        if enabled:
            self._on_format_change(self.download_format_var.get())

    def _set_processing(self, active: bool, button: str = "all"):
        """Enable/disable processing state (thread-safe)."""
        def _update():
            self.is_processing = active
            if active:
                self._set_controls_enabled(False)
                if button in ("all", "transcript"):
                    self.get_btn.configure(state="disabled", text="⏳ Processing...")
                if button in ("all", "video"):
                    self.download_video_btn.configure(state="disabled", text="⏳ Downloading...")
                self.cancel_btn.configure(state="normal", text="⛔ Hủy")
                self.progress_value_label.configure(text="...")
                self.progress_value_label.pack(side="right", padx=(8, 16), pady=6)
                self.progress_bar.pack(side="right", padx=(8, 0), fill="x", expand=True)
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start()
            else:
                self._set_controls_enabled(True)
                self.get_btn.configure(state="normal", text="⚡ Get Transcript")
                self.download_video_btn.configure(state="normal", text="⬇️ Download")
                self.cancel_btn.configure(state="disabled", text="⛔ Hủy")
                self.progress_bar.stop()
                self.progress_bar.set(0)
                self.progress_bar.pack_forget()
                self.progress_value_label.pack_forget()
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
            self._hide_download_waiting()
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
        
        close_btn = ctk.CTkButton(
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

                zoom_out_btn = ctk.CTkButton(
                    toolbar,
                    text="-",
                    width=36,
                    command=zoom_out,
                )
                zoom_out_btn.grid(row=0, column=2, padx=4, pady=10)

                zoom_in_btn = ctk.CTkButton(
                    toolbar,
                    text="+",
                    width=36,
                    command=zoom_in,
                )
                zoom_in_btn.grid(row=0, column=3, padx=4, pady=10)

                actual_btn = ctk.CTkButton(
                    toolbar,
                    text="100%",
                    width=64,
                    command=zoom_actual,
                )
                actual_btn.grid(row=0, column=4, padx=4, pady=10)

                fit_btn = ctk.CTkButton(
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
            self._set_status("⚠️ Vui lòng nhập YouTube URL", C_ORANGE)
            return

        try:
            video_id = extract_video_id(url)
        except ValueError as e:
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
                    info = get_video_info(url, self.cookie_browser_var.get())
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

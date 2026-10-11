"""OpenWhispr-Style Floating Voice Pill Overlay Widget.

Features:
- Frameless, always-on-top, transparent rounded floating capsule
- States:
  - "idle": Subtle compact 40x40 orb or hidden
  - "recording": 110x38 pill with mic icon + live-level animated waveform equalizer bars
  - "processing": 40x40 circle with glowing cyan/blue rotating spinner arc
  - "speaking": Soft glowing cyan ring
- OpenWhispr exact synthesized harmonic audio cues (C5->E5 start, D5->A4 stop)
"""

import time
import math
import threading
import queue
import tkinter as tk
import numpy as np
import pygame
import io
import wave


# Sound Synthesis matching OpenWhispr dictationCues.js
def _generate_tone(freq: float, duration: float = 0.09, attack: float = 0.015, sr: int = 44100, max_gain: float = 0.2) -> np.ndarray:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave_data = np.sin(2 * np.pi * freq * t)
    n_attack = int(sr * attack)
    env = np.zeros_like(wave_data)
    env[:n_attack] = np.linspace(0.001, max_gain, n_attack)
    env[n_attack:] = max_gain * np.exp(-4.5 * np.linspace(0, 1, len(wave_data) - n_attack))
    return wave_data * env

def _make_sound_cue(notes: list, sr: int = 44100):
    gap = np.zeros(int(sr * 0.025))
    tones = []
    for f in notes:
        tones.append(_generate_tone(f, sr=sr))
        tones.append(gap)
    audio = (np.concatenate(tones) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio.tobytes())
    buf.seek(0)
    return pygame.mixer.Sound(buf)


class FloatingVoicePill:
    def __init__(self, parent=None, on_trigger_voice=None, on_show_dashboard=None):
        self.parent = parent
        self.on_trigger_voice = on_trigger_voice
        self.on_show_dashboard = on_show_dashboard
        self.state = "idle"  # idle, recording, processing, speaking, listening
        self.current_level = 0.0
        self.target_level = 0.0
        self.spin_angle = 0
        self.is_running = True
        self.queue = queue.Queue()

        # Initialize Pygame Mixer for sound cues
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.start_cue = _make_sound_cue([523.25, 659.25])  # C5 -> E5 (OpenWhispr start)
            self.stop_cue = _make_sound_cue([587.33, 440.0])   # D5 -> A4 (OpenWhispr stop)
        except Exception:
            self.start_cue = None
            self.stop_cue = None

        self._is_visible = False
        self._last_active_time = 0.0

        if self.parent is not None:
            self._init_ui(self.parent)
        else:
            # Start Tkinter thread
            self.thread = threading.Thread(target=self._run_tk, daemon=True)
            self.thread.start()

        self.sfx_enabled = True

    def play_sfx(self, cue_type: str = "wake"):
        """Play OpenWhispr harmonic chime (wake: C5->E5, sleep: D5->A4)."""
        if not self.sfx_enabled:
            return
        try:
            if cue_type in ("wake", "start") and self.start_cue:
                self.start_cue.play()
            elif cue_type in ("sleep", "stop", "end") and self.stop_cue:
                self.stop_cue.play()
        except Exception:
            pass

    def set_state(self, state: str):
        """Set widget state: 'idle', 'recording', 'listening', 'processing', 'speaking'."""
        self.state = state
        self.queue.put(("state", state))

    def update_volume(self, vol: float):
        """Update live audio level (0.0 to 1.0)."""
        self.target_level = max(0.0, min(1.0, vol))

    def stop(self):
        """Cleanly destroy overlay widget immediately."""
        self.is_running = False
        self.queue.put(("destroy", None))

    def _init_ui(self, parent_widget):
        if parent_widget is not None:
            self.root = tk.Toplevel(parent_widget)
        else:
            self.root = tk.Tk()
        self.root.title("Jarvis Voice Pill")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Transparent background key on Windows
        TRANS_COLOR = "#010101"
        self.root.configure(bg=TRANS_COLOR)
        self.root.attributes("-transparentcolor", TRANS_COLOR)

        # Screen dimensions
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        self.w_idle = 44
        self.w_rec = 114
        self.h = 42

        # Anchor position pinned relative to bottom-right
        self.anchor_right_x = screen_w - 30
        self.anchor_y = screen_h - self.h - 60
        self._current_w = self.w_idle

        init_x = self.anchor_right_x - self.w_idle
        self.root.geometry(f"{self.w_idle}x{self.h}+{init_x}+{self.anchor_y}")

        self.canvas = tk.Canvas(
            self.root,
            width=self.w_idle,
            height=self.h,
            bg=TRANS_COLOR,
            highlightthickness=0,
            cursor="hand2"
        )
        self.canvas.pack(fill="both", expand=True)

        # Always visible as sleek resting orb
        self.root.deiconify()
        self._is_visible = True

        self._drag_start_x = 0
        self._drag_start_y = 0
        self._has_dragged = False

        def on_press(event):
            self._drag_start_x = event.x
            self._drag_start_y = event.y
            self._has_dragged = False

        def do_drag(event):
            dx = abs(event.x - self._drag_start_x)
            dy = abs(event.y - self._drag_start_y)
            if dx > 4 or dy > 4:
                self._has_dragged = True
            new_x = self.root.winfo_x() + (event.x - self._drag_start_x)
            new_y = self.root.winfo_y() + (event.y - self._drag_start_y)
            self.root.geometry(f"+{new_x}+{new_y}")
            self.anchor_right_x = new_x + self._current_w
            self.anchor_y = new_y

        def on_release(event):
            if not self._has_dragged:
                if self.on_trigger_voice:
                    self.on_trigger_voice()

        def on_double_click(event):
            if self.on_show_dashboard:
                self.on_show_dashboard()

        self.canvas.bind("<Button-1>", on_press)
        self.canvas.bind("<B1-Motion>", do_drag)
        self.canvas.bind("<ButtonRelease-1>", on_release)
        self.canvas.bind("<Double-Button-1>", on_double_click)

        # Start animation ticker
        self._animate()

    def _run_tk(self):
        self._init_ui(None)
        self.root.mainloop()

    def _draw_pill_bg(self, w, h, fill="#18181b", outline="#27272a"):
        r = (h - 2) / 2
        # Left circle
        self.canvas.create_oval(2, 2, 2 + 2*r, h - 2, fill=fill, outline=outline, width=1.5)
        # Right circle
        self.canvas.create_oval(w - 2 - 2*r, 2, w - 2, h - 2, fill=fill, outline=outline, width=1.5)
        # Middle rectangle
        self.canvas.create_rectangle(2 + r, 2, w - 2 - r, h - 2, fill=fill, outline=fill)
        # Top and bottom border lines
        self.canvas.create_line(2 + r, 2, w - 2 - r, 2, fill=outline, width=1.5)
        self.canvas.create_line(2 + r, h - 2, w - 2 - r, h - 2, fill=outline, width=1.5)

    def _draw_mic_icon(self, cx, cy, color="#ffffff"):
        # White circular mic badge
        r_outer = 13
        self.canvas.create_oval(cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer, outline=color, width=1.5)
        # Inner vertical sound bars inside circle
        self.canvas.create_line(cx - 4, cy - 4, cx - 4, cy + 4, fill=color, width=1.5)
        self.canvas.create_line(cx, cy - 7, cx, cy + 7, fill=color, width=2)
        self.canvas.create_line(cx + 4, cy - 4, cx + 4, cy + 4, fill=color, width=1.5)

    def _animate(self):
        if not self.is_running:
            try:
                self.root.withdraw()
                self.root.destroy()
            except Exception:
                pass
            return

        # Process any pending events
        while not self.queue.empty():
            msg, val = self.queue.get_nowait()
            if msg == "state":
                self.state = val
            elif msg == "destroy":
                try:
                    self.root.quit()
                    self.root.destroy()
                except Exception:
                    pass
                return

        # Always maintain visibility (never withdraw into thin air)
        if not self._is_visible:
            try:
                self.root.deiconify()
                self._is_visible = True
            except Exception:
                pass

        # Smooth dynamic geometry expansion / contraction
        target_w = self.w_rec if self.state in ("recording", "listening", "speaking") else self.w_idle
        if getattr(self, "_current_w", None) != target_w:
            self._current_w = target_w
            cur_x = self.anchor_right_x - target_w
            self.root.geometry(f"{target_w}x{self.h}+{cur_x}+{self.anchor_y}")
            self.canvas.configure(width=target_w)

        self.canvas.delete("all")
        self.current_level += (self.target_level - self.current_level) * 0.35
        mid_y = self.h / 2

        if self.state in ("recording", "listening"):
            # Expand to 114px pill with live audio level detection (OpenWhispr style)
            w = self.w_rec
            is_recording = (self.state == "recording")
            outline_col = "#38bdf8" if is_recording else "#0284c7"
            self._draw_pill_bg(w, self.h, fill="#16161a", outline=outline_col)
            self._draw_mic_icon(20, mid_y, color="#38bdf8" if is_recording else "#0284c7")

            start_x = 42
            end_x = 104
            level = max(0.0, min(1.0, self.current_level))

            # OpenWhispr sound detection:
            # Flat line when quiet (< 0.05). Dynamic undulating wave when speaking!
            if level < 0.05:
                line_color = "#94a3b8" if is_recording else "#64748b"
                self.canvas.create_line(
                    start_x, mid_y, end_x, mid_y,
                    fill=line_color,
                    width=2.0,
                    capstyle="round"
                )
            else:
                num_points = 25
                coords = []
                t_time = time.time() * (14 if is_recording else 10)
                wave_color = "#38bdf8" if is_recording else "#00e5ff"
                max_amp = (self.h * 0.38)
                for j in range(num_points):
                    ratio = j / (num_points - 1)
                    px = start_x + ratio * (end_x - start_x)
                    envelope = math.sin(ratio * math.pi)
                    w1 = math.sin(t_time + ratio * 3.5 * math.pi)
                    w2 = 0.35 * math.sin(t_time * 1.8 + ratio * 7.0 * math.pi)
                    py = mid_y + (max_amp * level * envelope) * (w1 + w2)
                    coords.extend([px, py])

                self.canvas.create_line(
                    coords,
                    smooth=True,
                    fill=wave_color,
                    width=2.5,
                    capstyle="round"
                )

        elif self.state == "speaking":
            # 114px pill with undulating voice playback wave
            w = self.w_rec
            self._draw_pill_bg(w, self.h, fill="#16161a", outline="#00e676")
            self._draw_mic_icon(20, mid_y, color="#00e676")

            start_x = 42
            end_x = 104
            level = max(0.25, min(1.0, self.current_level))

            num_points = 25
            coords = []
            t_time = time.time() * 12
            max_amp = (self.h * 0.38)
            for j in range(num_points):
                ratio = j / (num_points - 1)
                px = start_x + ratio * (end_x - start_x)
                envelope = math.sin(ratio * math.pi)
                w1 = math.sin(t_time + ratio * 3.2 * math.pi)
                w2 = 0.3 * math.sin(t_time * 2.0 + ratio * 6.5 * math.pi)
                py = mid_y + (max_amp * level * envelope) * (w1 + w2)
                coords.extend([px, py])

            self.canvas.create_line(
                coords,
                smooth=True,
                fill="#00e676",
                width=2.5,
                capstyle="round"
            )

        elif self.state == "processing":
            # Circular 44x42 orb with rotating cyan spinner ring
            w = self.w_idle
            cx, cy = w / 2, mid_y
            r = 18
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#18181b", outline="#27272a", width=1.5)
            self._draw_mic_icon(cx, cy, color="#00dcff")

            # Rotating glowing cyan arc
            self.spin_angle = (self.spin_angle + 14) % 360
            self.canvas.create_arc(
                cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1,
                start=self.spin_angle,
                extent=100,
                outline="#00dcff",
                width=2.5,
                style="arc"
            )

        else: # idle
            # Sleek subtle resting orb with glowing blue ring and mic badge
            w = self.w_idle
            cx, cy = w / 2, mid_y
            r = 18
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#121215", outline="#2563eb", width=1.8)
            self._draw_mic_icon(cx, cy, color="#60a5fa")

        # Loop at ~35 FPS for buttery smooth animation
        self.root.after(28, self._animate)



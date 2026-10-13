# Jarvis AI - Fast Voice Copilot for Windows ⚡

A lightning-fast, minimalist AI voice copilot and desktop system agent for Windows. Powered by **NVIDIA Parakeet-EOU INT8 speech recognition** (<300ms latency) and **DeepSeek 4.1 Flash** via OpenRouter.

Runs quietly in your Windows system tray, features an OpenWhispr-style floating voice pill overlay, and executes real system actions instantly.

---

## 🚀 1-Click Quick Start (For Friends)

### Download GitHub Release (Recommended)
1. Download **`Jarvis-Release.zip`** from [GitHub Releases](https://github.com/shantoshdurai/Offline-Jarvis-Assistant/releases).
2. Extract the folder anywhere on your PC (e.g. `C:\Jarvis` or in your `Downloads` folder).
3. Double-click **`setup.bat`** (or directly double-click **`Jarvis.exe`**).
   - *It will automatically set up the Python environment, install required packages, and download the fast 112MB speech model.*
4. Open the generated **`.env`** file in Notepad and paste your OpenRouter API key:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   ```
   *(Get an API key in 10 seconds at [openrouter.ai/keys](https://openrouter.ai/keys) — free tier supported!)*
5. Double-click **`Jarvis.exe`** to launch! 🎉

---

## 🎙️ How to Use

- **Wake Word**: Say **`"Hey Jarvis"`** anytime. Jarvis wakes up, listens to your command, and responds.
- **Push-to-Talk Hotkey**: Press **`Ctrl + Shift + Space`** or **`Ctrl + Alt + J`** anywhere in Windows.
- **Floating Voice Pill**: A sleek transparent capsule appears with a live audio waveform, speaks the response, and tucks away.
- **Dashboard GUI**: Click the blue tray icon or search **Jarvis** in the Windows Start Menu to open the full dashboard (activity history, chat, telemetry, and settings).
- **Run on Windows Startup**: Double-click **`enable_startup.bat`** to run Jarvis silently in the background on boot.

---

## ⚡ What Jarvis Can Do

Jarvis is a full system-level agent with instant sub-50ms local execution:

| Category | Spoken Command Example | Action |
|---|---|---|
| **System Telemetry** | *"What is the system condition?"* / *"Check CPU and GPU"* | Live CPU%, RAM, NVIDIA GPU VRAM & LAN bandwidth |
| **Media Playback** | *"Play Loki soundtrack on YouTube"* | Resolves and plays top video directly |
| **App Launching** | *"Open VS Code"* / *"Launch Helium"* / *"Open Terminal"* | Launches application natively |
| **Smart Folders** | *"Open work folder"* / *"Show downloads"* | Opens folder in Windows Explorer (`C:\work`, etc.) |
| **Screenshots** | *"Open the last screenshot"* / *"Take a screenshot"* | Opens newest screenshot from Pictures |
| **Hardware** | *"Set volume to 50"* / *"Increase brightness"* | Direct master volume & monitor brightness control |
| **File Organization** | *"Organize my downloads folder"* | Automatically groups loose files into categorized folders |
| **Web Research** | *"Search web for Claude 3.5 Sonnet benchmarks"* | Live web search & conversational summary |
| **Persistent Memory** | *"Remember my favorite music is Loki"* / *"What do you recall?"* | Retains personal user facts across sessions |

---

## ⚙️ Manual Developer Setup

If cloning directly from source:
```powershell
git clone https://github.com/shantoshdurai/Offline-Jarvis-Assistant.git
cd Offline-Jarvis-Assistant
setup.bat
```

Run comprehensive benchmark suite:
```powershell
.\venv\Scripts\python.exe eval_agent.py
```

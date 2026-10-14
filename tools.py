import time
import threading
import ctypes
import os
import sys
import subprocess
import webbrowser
import shutil
import urllib.parse
import urllib.request
import json
from datetime import datetime
import re
import ast
import difflib

FIREFOX_PATHS = [
    r"C:\Program Files\Mozilla Firefox\firefox.exe",
    r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
]

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
]

def get_firefox_exe():
    for p in FIREFOX_PATHS:
        if os.path.exists(p):
            return p
    return None

def get_chrome_exe():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    return None

HELIUM_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\imput\Helium\Application\chrome.exe"),
    r"C:\Users\Dog\AppData\Local\imput\Helium\Application\chrome.exe",
    os.path.expandvars(r"%PROGRAMFILES%\Helium\Helium.exe"),
    os.path.expandvars(r"%PROGRAMFILES(X86)%\Helium\Helium.exe"),
]

def get_helium_exe():
    for p in HELIUM_PATHS:
        if os.path.exists(p):
            return p
    return None

def get_default_browser_exe():
    """Returns the executable path and name for the user's default browser (Helium by default)."""
    he = get_helium_exe()
    if he:
        return he, "Helium"
    ch = get_chrome_exe()
    if ch:
        return ch, "Chrome"
    ff = get_firefox_exe()
    if ff:
        return ff, "Firefox"
    return None, "Default Browser"

def open_in_helium(url: str) -> bool:
    """Opens a URL in Helium browser.
    If Helium is running, brings it to foreground, creates a new tab (Ctrl+T), and pastes the clean URL.
    If Helium is closed, launches the Helium process directly with the last active profile.
    """
    he = get_helium_exe()
    if not he:
        return False

    user32 = ctypes.windll.user32
    try:
        hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

    # Check for active Helium window
    helium_hwnd = None
    try:
        import win32gui, win32con
        def _enum_cb(h, _):
            nonlocal helium_hwnd
            if win32gui.IsWindowVisible(h):
                title = win32gui.GetWindowText(h)
                cls = win32gui.GetClassName(h)
                if "Helium" in title and "Chrome" in cls:
                    helium_hwnd = h
            return True
        win32gui.EnumWindows(_enum_cb, None)
    except Exception:
        pass

    if helium_hwnd:
        try:
            import win32gui, win32con, win32clipboard
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(url, win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()

            if win32gui.IsIconic(helium_hwnd):
                win32gui.ShowWindow(helium_hwnd, win32con.SW_RESTORE)
            user32.SetForegroundWindow(helium_hwnd)
            time.sleep(0.12)

            KEYEVENTF_KEYUP = 0x0002
            VK_CONTROL = 0x11
            VK_RETURN = 0x0D

            def _combo(*vks):
                for vk in vks:
                    user32.keybd_event(vk, 0, 0, 0)
                for vk in reversed(vks):
                    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

            # Ctrl+T to open new tab
            _combo(VK_CONTROL, ord('T'))
            time.sleep(0.18)

            # Ctrl+V to paste URL
            _combo(VK_CONTROL, ord('V'))
            time.sleep(0.08)

            # Enter to navigate
            _combo(VK_RETURN)
            return True
        except Exception as e:
            print(f"[Notice] Helium hotkey navigation fallback: {e}")

    # Fallback when Helium is not currently open
    profile = "Profile 1"
    local_state = os.path.expandvars(r"%LOCALAPPDATA%\imput\Helium\User Data\Local State")
    if os.path.exists(local_state):
        try:
            with open(local_state, 'r', encoding='utf-8') as f:
                data = json.load(f)
                profile = data.get("profile", {}).get("last_used", "Profile 1")
        except Exception:
            pass

    flags = getattr(subprocess, "DETACHED_PROCESS", 0)
    try:
        subprocess.Popen([he, f'--profile-directory={profile}', url], creationflags=flags)
        return True
    except Exception:
        try:
            subprocess.Popen([he, url], creationflags=flags)
            return True
        except Exception:
            return False

def browser_control(action: str, tab_index: int = None, url: str = None) -> str:
    """Controls browser tabs, URL navigation, and media playback across Firefox, Chrome, and Edge."""
    action = (action or "").lower().strip()

    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002
    VK_CONTROL = 0x11
    VK_SHIFT = 0x10
    VK_TAB = 0x09
    VK_ESCAPE = 0x1B
    VK_F5 = 0x74

    def send_combo(*vks):
        for vk in vks:
            user32.keybd_event(vk, 0, 0, 0)
        for vk in reversed(vks):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    if action in ("play_pause", "play", "pause", "resume", "toggle_play"):
        user32.keybd_event(ord('K'), 0, 0, 0)
        user32.keybd_event(ord('K'), 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(0xB3, 0, 0, 0)
        user32.keybd_event(0xB3, 0, KEYEVENTF_KEYUP, 0)
        return "Playback started." if action in ("play", "resume") else "Playback toggled."

    elif action in ("next_tab", "switch_next_tab"):
        send_combo(VK_CONTROL, VK_TAB)
        return "Switched to next tab."

    elif action in ("previous_tab", "prev_tab", "switch_prev_tab"):
        send_combo(VK_CONTROL, VK_SHIFT, VK_TAB)
        return "Switched to previous tab."

    elif action in ("switch_tab", "go_to_tab"):
        idx = int(tab_index or 1)
        if idx < 1: idx = 1
        if idx > 9: idx = 9
        vk_num = 0x30 + idx
        send_combo(VK_CONTROL, vk_num)
        return f"Switched to tab {idx}."

    elif action in ("close_tab", "close_current_tab"):
        send_combo(VK_CONTROL, ord('W'))
        return "Closed active tab."

    elif action in ("reopen_tab", "undo_close_tab"):
        send_combo(VK_CONTROL, VK_SHIFT, ord('T'))
        return "Reopened closed tab."

    elif action in ("new_tab", "open_new_tab"):
        if url:
            open_url(url)
            return f"Opened {url} in new tab."
        send_combo(VK_CONTROL, ord('T'))
        return "Opened new tab."

    elif action in ("reload_tab", "refresh_tab", "refresh"):
        send_combo(VK_F5)
        return "Refreshed active tab."

    elif action in ("get_url", "read_url", "current_url"):
        send_combo(VK_CONTROL, ord('L'))
        time.sleep(0.08)
        send_combo(VK_CONTROL, ord('C'))
        time.sleep(0.08)
        send_combo(VK_ESCAPE)

        read_url = ""
        try:
            import win32clipboard, win32con
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                read_url = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
        except Exception:
            pass

        if read_url and ("http://" in read_url or "https://" in read_url or "." in read_url):
            return f"Active tab URL is {read_url.strip()}."
        return "Could not read active tab URL."

    return f"Unknown browser action: '{action}'."

def play_video(query_or_target, browser=None):
    """Search for the top video on YouTube and immediately open and play it directly."""
    cleaned_query = query_or_target.strip().strip("'\"")
    for prefix in ["play ", "watch ", "listen to "]:
        if cleaned_query.lower().startswith(prefix):
            cleaned_query = cleaned_query[len(prefix):].strip()

    search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(cleaned_query)}"
    target_url = search_url
    try:
        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        vids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
        if vids:
            target_url = f"https://www.youtube.com/watch?v={vids[0]}&autoplay=1"
    except Exception:
        pass

    browser_lower = (browser or "").lower()
    if "helium" in browser_lower:
        if open_in_helium(target_url):
            return f"Playing '{cleaned_query}' on YouTube in Helium."
    elif "firefox" in browser_lower:
        ff = get_firefox_exe()
        if ff:
            subprocess.Popen([ff, target_url])
            return f"Playing '{cleaned_query}' on YouTube in Firefox."
    elif "chrome" in browser_lower:
        ch = get_chrome_exe()
        if ch:
            subprocess.Popen([ch, target_url])
            return f"Playing '{cleaned_query}' on YouTube in Chrome."
    else:
        # User default browser: Helium
        if open_in_helium(target_url):
            return f"Playing '{cleaned_query}' on YouTube in Helium."

    webbrowser.open(target_url)
    return f"Playing '{cleaned_query}' on YouTube."


def get_friendly_site_name(url: str, raw_target: str) -> str:
    """Extracts a clean, voice-friendly description of what was opened."""
    url_lower = url.lower()
    if "chatgpt.com" in url_lower:
        return "ChatGPT"
    elif "youtube.com" in url_lower:
        return "YouTube"
    elif "github.com" in url_lower:
        return "GitHub"
    elif "leetcode.com" in url_lower:
        return "LeetCode"
    elif "google.com/search?q=" in url_lower:
        q = urllib.parse.unquote(url.split("search_query=")[-1] if "search_query=" in url else url.split("q=")[-1])
        q = q.replace("+", " ").strip()
        return f"search for '{q}'"
    elif "reddit.com" in url_lower:
        return "Reddit"
    elif "twitter.com" in url_lower or "x.com" in url_lower:
        return "X"
    elif "wikipedia.org" in url_lower:
        return "Wikipedia"
    else:
        raw_clean = raw_target.replace("http://", "").replace("https://", "").replace("www.", "").strip("/")
        return raw_clean or "the webpage"

def open_url(url_or_target, browser=None):
    """Opens a website or URL in Firefox, Chrome, or default browser."""
    url = url_or_target.strip().strip("'\"")
    if "youtube.com/results?search_query=" in url:
        q = urllib.parse.unquote(url.split("search_query=")[-1])
        return play_video(q, browser=browser)
    elif url.lower().startswith("play "):
        return play_video(url[5:], browser=browser)
    elif url.lower() == "youtube":
        url = "https://www.youtube.com"
    elif url.lower() == "leetcode":
        url = "https://leetcode.com/problemset/"
    elif url.lower() == "github":
        url = "https://github.com"
    elif not url.startswith("http://") and not url.startswith("https://"):
        if "." in url and " " not in url:
            url = f"https://{url}"
        else:
            url = f"https://www.google.com/search?q={urllib.parse.quote(url)}"

    friendly_name = get_friendly_site_name(url, url_or_target)
    browser_lower = (browser or "").lower()
    if "helium" in browser_lower:
        if open_in_helium(url):
            return f"Opened {friendly_name} in Helium."
    elif "firefox" in browser_lower:
        ff = get_firefox_exe()
        if ff:
            subprocess.Popen([ff, url])
            return f"Opened {friendly_name} in Firefox."
    elif "chrome" in browser_lower:
        ch = get_chrome_exe()
        if ch:
            subprocess.Popen([ch, url])
            return f"Opened {friendly_name} in Chrome."
    else:
        # User default browser: Helium
        if open_in_helium(url):
            return f"Opened {friendly_name} in Helium."

    webbrowser.open(url)
    return f"Opened {friendly_name}."

def get_leetcode_daily():
    """Queries LeetCode public GraphQL API for today's active coding challenge."""
    url = "https://leetcode.com/graphql"
    query = """
    query questionOfToday {
        activeDailyCodingChallengeQuestion {
            date
            link
            question {
                questionFrontendId
                title
                titleSlug
            }
        }
    }
    """
    body = json.dumps({"query": query}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
            daily = data.get("data", {}).get("activeDailyCodingChallengeQuestion", {})
            q = daily.get("question", {})
            title = q.get("title")
            slug = q.get("titleSlug")
            return title, slug
    except Exception:
        return None, None

def check_leetcode_problem(slug):
    """Verifies whether a problem slug exists on LeetCode via GraphQL."""
    if not slug:
        return None
    url = "https://leetcode.com/graphql"
    query = """
    query questionTitle($titleSlug: String!) {
        question(titleSlug: $titleSlug) {
            questionFrontendId
            title
            titleSlug
        }
    }
    """
    body = json.dumps({
        "query": query,
        "variables": {"titleSlug": slug}
    }).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
            return data.get("data", {}).get("question")
    except Exception:
        return None

def open_leetcode(problem_query="", browser=None):
    """
    Intelligently opens a LeetCode problem, today's daily challenge,
    or falls back frankly to problem search if the exact link is uncertain.
    Returns (action_msg, speech_response).
    """
    t = (problem_query or "").strip().strip("'\"").lower()

    # 1. Daily Challenge Request
    if any(w in t for w in ["today", "daily", "challenge of today", "today's"]):
        title, slug = get_leetcode_daily()
        if slug and title:
            url = f"https://leetcode.com/problems/{slug}/"
            open_url(url, browser=browser)
            action = f"Opened today's LeetCode daily challenge: '{title}' ({url})"
            speech = f"I fetched today's LeetCode daily challenge for you: {title}. Opening it now in your browser."
            return action, speech
        else:
            url = "https://leetcode.com/problemset/"
            open_url(url, browser=browser)
            action = f"Opened LeetCode problem set ({url})"
            speech = "I opened the LeetCode problem set for you. I couldn't reach the daily challenge server right now, but today's problem is pinned at the top."
            return action, speech

    # Clean query of filler words
    clean = re.sub(r'^(hey\s+jarvis\s*,?\s*|jarvis\s*,?\s*)', '', t)
    clean = re.sub(r'^(can\s+you\s+)?(open|show|go\s+to|launch|give\s+me)\s+(leetcode\s+)?(problem\s+|question\s+)?', '', clean).strip()
    clean = re.sub(r'\b(on\s+leetcode|in\s+leetcode|from\s+leetcode|leetcode)\b', '', clean).strip()
    clean = re.sub(r'\b(in\s+my\s+browser|in\s+browser|in\s+firefox|in\s+chrome|please|for\s+me|website|solution)\b', '', clean).strip()
    clean = re.sub(r'^(for|about|with|the)\s+', '', clean).strip()
    clean = clean.strip('\'".,?! ')

    # 2. General / Empty -> open Problemset homepage
    if not clean or clean in ["all", "list", "set", "problemset", "problems", "home", "homepage"]:
        url = "https://leetcode.com/problemset/"
        open_url(url, browser=browser)
        action = f"Opened LeetCode problem set ({url})"
        speech = "Opening the LeetCode problem set homepage in your browser."
        return action, speech

    # 3. Form candidate slug
    candidate_slug = re.sub(r'[^a-zA-Z0-9\s-]', '', clean).strip().replace(" ", "-").replace("_", "-")
    candidate_slug = re.sub(r'-+', '-', candidate_slug).lower()
    if "-" in candidate_slug and candidate_slug.split("-")[0].isdigit():
        candidate_slug = "-".join(candidate_slug.split("-")[1:])

    prob_info = check_leetcode_problem(candidate_slug) if candidate_slug else None
    if prob_info and prob_info.get("titleSlug"):
        title = prob_info.get("title")
        slug = prob_info.get("titleSlug")
        num = prob_info.get("questionFrontendId", "")
        url = f"https://leetcode.com/problems/{slug}/"
        open_url(url, browser=browser)
        action = f"Opened LeetCode problem '{title}' (#{num}) ({url})"
        speech = f"Opening LeetCode problem {title} in your browser."
        return action, speech
    else:
        # Frank fallback: do not guess a link that might 404! Open search and tell user frankly.
        search_url = f"https://leetcode.com/problemset/?search={urllib.parse.quote(clean)}"
        open_url(search_url, browser=browser)
        action = f"Opened LeetCode search for '{clean}' ({search_url})"
        speech = f"I opened the LeetCode search for {clean}. To be frank, I wasn't completely sure of the direct link, so I opened the search results so you can select the exact problem."
        return action, speech

_APPS_CACHE = None
_APPS_CACHE_TIME = 0.0

def get_installed_apps_catalog(force_refresh=False):
    """Discovers and caches installed applications across Windows Desktop and Start Menu."""
    global _APPS_CACHE, _APPS_CACHE_TIME
    import time
    if not force_refresh and _APPS_CACHE is not None and (time.time() - _APPS_CACHE_TIME < 120):
        return _APPS_CACHE

    search_dirs = [
        os.path.join(os.path.expanduser('~'), 'Desktop'),
        os.path.join(os.environ.get('PUBLIC', r'C:\Users\Public'), 'Desktop'),
        os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs'),
        os.path.join(os.environ.get('PROGRAMDATA', r'C:\ProgramData'), r'Microsoft\Windows\Start Menu\Programs'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs'),
    ]

    apps = {}
    ignored_keywords = ('uninstall', 'remove', 'help', 'readme', 'documentation', 'install', 'update', 'settings')
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        try:
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(('.lnk', '.exe', '.url')):
                        stem = os.path.splitext(f)[0]
                        stem_lower = stem.lower()
                        if any(bad in stem_lower for bad in ignored_keywords):
                            continue
                        norm_stem = re.sub(r'[^a-zA-Z0-9]', '', stem_lower)
                        if norm_stem and norm_stem not in apps:
                            apps[norm_stem] = {
                                "stem": stem,
                                "path": os.path.join(root, f),
                                "filename": f
                            }
        except Exception:
            continue

    _APPS_CACHE = apps
    _APPS_CACHE_TIME = time.time()
    return apps

def list_installed_apps(filter_query=""):
    """
    Returns a clean summary of installed software and applications on the PC.
    If filter_query is provided, filters applications matching the query.
    """
    catalog = get_installed_apps_catalog()
    q = (filter_query or "").strip().lower()

    items = list(catalog.values())
    if q:
        filtered = [it for it in items if q in it["stem"].lower()]
    else:
        # Filter down to prominent user applications (exclude small CLI helper scripts)
        filtered = [it for it in items if not it["stem"].lower().startswith(('activate-', 'accelerate-', 'cli-'))]

    names = sorted(list({it["stem"] for it in filtered}))
    if not names:
        return f"No installed applications found matching '{filter_query}'."

    sample = names[:15]
    res = f"Found {len(names)} installed applications on your PC: " + ", ".join(sample)
    if len(names) > 15:
        res += f", and {len(names) - 15} more."
    return res

def find_app_shortcut(app_name):
    """
    Dynamically discovers application shortcuts (.lnk, .url) and executables (.exe)
    across Windows Desktop, Start Menu, and AppData directories.
    Returns (path, display_name) or (None, None).
    """
    clean_query = (app_name or "").strip().lower()
    clean_query = re.sub(r'^(the|open|launch|run|start)\s+', '', clean_query)
    clean_query = re.sub(r'\s+(app|application|software|program|ide)$', '', clean_query).strip()
    norm_query = re.sub(r'[^a-zA-Z0-9]', '', clean_query)
    if not norm_query:
        return None, None

    catalog = get_installed_apps_catalog()

    # 1. Exact normalized match (e.g. 'antigravity' == 'antigravity')
    if norm_query in catalog:
        entry = catalog[norm_query]
        return entry["path"], entry["stem"]

    # 2. Query is prefix match (e.g. 'blender' matches 'blender52')
    for norm_stem, entry in catalog.items():
        if norm_stem.startswith(norm_query):
            return entry["path"], entry["stem"]

    return None, None

def open_app(app_name):
    """Opens local applications dynamically, asking clarification if misheard or ambiguous."""
    raw_name = (app_name or "").strip().strip("'\"")
    name = raw_name.lower()
    if not name:
        return "Please specify an application to open."

    # Built-in handlers for shell components and browsers
    if "helium" in name or name in ("browser", "my browser", "default browser", "the browser"):
        he = get_helium_exe()
        if he:
            subprocess.Popen([he])
            return "Launched Helium Browser."
        subprocess.Popen(["start", "helium"], shell=True)
        return "Launched Helium."
    elif "firefox" in name:
        ff = get_firefox_exe()
        if ff:
            subprocess.Popen([ff])
            return "Launched Mozilla Firefox."
        subprocess.Popen(["start", "firefox"], shell=True)
        return "Launched Firefox."
    elif "chrome" in name:
        ch = get_chrome_exe()
        if ch:
            subprocess.Popen([ch])
            return "Launched Google Chrome."
        subprocess.Popen(["start", "chrome"], shell=True)
        return "Launched Chrome."
    elif "code" in name or "vscode" in name:
        target, title = find_app_shortcut("code")
        if target:
            try:
                os.startfile(target)
                return "Launched Visual Studio Code."
            except Exception:
                pass
        subprocess.Popen(["code"], shell=True)
        return "Launched Visual Studio Code."
    elif "notepad" in name:
        subprocess.Popen(["notepad.exe"])
        return "Launched Notepad."
    elif "terminal" in name or "powershell" in name:
        subprocess.Popen(["powershell.exe"])
        return "Launched PowerShell Terminal."
    elif "cmd" in name or "command prompt" in name:
        subprocess.Popen(["cmd.exe"])
        return "Launched Command Prompt."
    elif "calc" in name or "calculator" in name:
        subprocess.Popen(["calc.exe"])
        return "Launched Calculator."
    elif "explorer" in name or "files" in name or "folder" in name:
        subprocess.Popen(["explorer.exe"])
        return "Opened File Explorer."

    # Dynamic application shortcut & executable discovery
    target_path, display_title = find_app_shortcut(name)
    if target_path:
        try:
            os.startfile(target_path)
            return f"Launched {display_title}."
        except Exception as e:
            return f"Found {display_title} but could not launch it: {e}"

    # Check system PATH executable via shutil.which
    which_path = shutil.which(name) or shutil.which(f"{name}.exe")
    if which_path:
        try:
            subprocess.Popen([which_path])
            return f"Launched {os.path.splitext(os.path.basename(which_path))[0]}."
        except Exception as e:
            return f"Found {name} on PATH but failed to launch: {e}"

    # Ambiguity & Mishearing Detection: check installed applications catalog
    catalog = get_installed_apps_catalog()
    all_stems = [entry["stem"] for entry in catalog.values()]

    # Check substring matches (e.g. "studio" -> OBS Studio, Visual Studio Code, Android Studio)
    raw_sub = [s for s in all_stems if name in s.lower()]
    # Normalize variants (e.g. Antigravity and Antigravity IDE -> Antigravity)
    unique_sub = sorted(list({re.sub(r'\s+ide$', '', s, flags=re.IGNORECASE) for s in raw_sub}))

    if len(unique_sub) > 1 and len(unique_sub) <= 5:
        return f"I found multiple apps matching '{raw_name}': {', '.join(unique_sub[:3])}. Which one would you like to open?"
    elif len(unique_sub) == 1:
        return f"I couldn't find '{raw_name}'. Did you mean {unique_sub[0]}?"

    # Fuzzy match for misheard or typoed names (e.g. "claud", "diskord")
    close_matches = difflib.get_close_matches(raw_name, all_stems, n=3, cutoff=0.5)
    if not close_matches:
        close_matches = difflib.get_close_matches(name, [s.lower() for s in all_stems], n=3, cutoff=0.5)
        if close_matches:
            lower_to_stem = {s.lower(): s for s in all_stems}
            close_matches = [lower_to_stem.get(c, c) for c in close_matches]

    if close_matches:
        best = close_matches[0]
        return f"I couldn't find '{raw_name}'. Did you mean {best}?"

    return f"I couldn't find an installed application matching '{raw_name}'. You can ask me to list your installed applications."

def close_app(app_name):
    """Closes or terminates a running application, browser, or active window."""
    name = (app_name or "").strip().strip("'\"").lower()
    if not name:
        return "Please specify the application to close."

    targets = []
    display_name = app_name

    if "helium" in name or name in ("browser", "my browser", "the browser"):
        try:
            import psutil
            killed = False
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    exe = (proc.info.get('exe') or '').lower()
                    if 'helium' in exe:
                        proc.kill()
                        killed = True
                except Exception:
                    pass
            if killed:
                return "Closed Helium."
        except Exception:
            pass
        targets = ["chrome.exe"]
        display_name = "Helium"
    elif "chrome" in name:
        targets = ["chrome.exe"]
        display_name = "Google Chrome"
    elif "firefox" in name:
        targets = ["firefox.exe"]
        display_name = "Mozilla Firefox"
    elif "edge" in name:
        targets = ["msedge.exe"]
        display_name = "Microsoft Edge"
    elif "code" in name or "vscode" in name:
        targets = ["Code.exe"]
        display_name = "Visual Studio Code"
    elif "notepad" in name:
        targets = ["notepad.exe"]
        display_name = "Notepad"
    elif "calc" in name or "calculator" in name:
        targets = ["CalculatorApp.exe", "calc.exe"]
        display_name = "Calculator"
    elif "spotify" in name:
        targets = ["Spotify.exe"]
        display_name = "Spotify"
    elif "blender" in name:
        targets = ["blender.exe"]
        display_name = "Blender"
    elif "terminal" in name or "powershell" in name:
        targets = ["WindowsTerminal.exe", "powershell.exe"]
        display_name = "Terminal"
    elif "cmd" in name or "command prompt" in name:
        targets = ["cmd.exe"]
        display_name = "Command Prompt"
    elif any(k in name for k in ("current", "active", "this window", "the window", "that window")):
        import ctypes
        VK_MENU = 0x12  # Alt
        VK_F4 = 0x73    # F4
        ctypes.windll.user32.keybd_event(VK_MENU, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_F4, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_F4, 0, 2, 0)
        ctypes.windll.user32.keybd_event(VK_MENU, 0, 2, 0)
        return "Closed the active window."
    else:
        proc = name if name.endswith(".exe") else f"{name}.exe"
        targets = [proc]
        display_name = app_name

    closed_any = False
    for exe in targets:
        try:
            res = subprocess.run(["taskkill", "/F", "/IM", exe, "/T"], capture_output=True, text=True)
            if res.returncode == 0:
                closed_any = True
        except Exception:
            pass

    if closed_any:
        return f"Closed {display_name}."
    return f"{display_name} was closed or not running."

def take_screenshot(filename=None):
    """Takes a desktop screenshot and saves it."""
    pictures_dir = os.path.join(os.path.expanduser("~"), "Pictures")
    if not os.path.exists(pictures_dir):
        pictures_dir = "."
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(pictures_dir, f"screenshot_{timestamp}.png")
    else:
        filename = filename.strip().strip("'\"")
        if not os.path.isabs(filename):
            filename = os.path.join(pictures_dir, filename)

    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(filename)
        return f"Screenshot saved successfully to {filename}"
    except Exception:
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=filename)
            return f"Screenshot saved successfully to {filename}"
        except Exception as e2:
            return f"Failed to take screenshot: {e2}"

def inspect_screen():
    """
    Offline Vision: Captures the desktop and extracts on-screen text/code
    using Windows 10/11 native hardware-accelerated OCR.
    """
    try:
        from PIL import ImageGrab
        import io, asyncio
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()
        
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.graphics.imaging import BitmapDecoder
        from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
        
        async def do_ocr():
            stream = InMemoryRandomAccessStream()
            writer = DataWriter(stream)
            writer.write_bytes(data)
            await writer.store_async()
            await writer.flush_async()
            stream.seek(0)
            decoder = await BitmapDecoder.create_async(stream)
            software_bitmap = await decoder.get_software_bitmap_async()
            engine = OcrEngine.try_create_from_user_profile_languages()
            res = await engine.recognize_async(software_bitmap)
            return "\n".join([line.text for line in res.lines if line.text.strip()])
            
        text = asyncio.run(do_ocr())
        return text.strip() if text.strip() else "(Screen appears to be blank or contains no readable text)"
    except Exception as e:
        return f"(Screen OCR error: {e})"

def adjust_brightness(action="increase", value=None):
    """Controls laptop screen brightness (increase, decrease, set)."""
    try:
        import screen_brightness_control as sbc
        curr = sbc.get_brightness()
        curr_val = curr[0] if isinstance(curr, list) and curr else 50
        
        if action == "set" and value is not None:
            new_val = max(0, min(100, int(value)))
            sbc.set_brightness(new_val)
            return f"Brightness set to {new_val}%."
        elif "inc" in action or "up" in action or "more" in action or "+" in action:
            new_val = min(100, curr_val + (int(value) if value else 15))
            sbc.set_brightness(new_val)
            return f"Brightness increased to {new_val}%."
        elif "dec" in action or "down" in action or "less" in action or "-" in action:
            new_val = max(0, curr_val - (int(value) if value else 15))
            sbc.set_brightness(new_val)
            return f"Brightness decreased to {new_val}%."
        else:
            return f"Current brightness is {curr_val}%."
    except Exception as e:
        return f"Failed to adjust brightness: {e}"

def adjust_volume(action="increase", value=None):
    """Controls Windows master volume using pycaw with fallback to user32 keystrokes."""
    import ctypes

    # Try pycaw first for accurate percentage and scalar volume setting
    try:
        from pycaw.pycaw import AudioUtilities
        devices = AudioUtilities.GetSpeakers()
        endpoint = devices.EndpointVolume

        if (action == "set" or str(action).isdigit()) or value is not None:
            target = int(value) if value is not None else int(action)
            target = max(0, min(100, target))
            endpoint.SetMasterVolumeLevelScalar(target / 100.0, None)
            return f"Volume set to {target}%."
        elif "mute" in str(action).lower():
            is_muted = endpoint.GetMute()
            endpoint.SetMute(not is_muted, None)
            return "Volume muted." if not is_muted else "Volume unmuted."
        elif "up" in str(action) or "inc" in str(action) or "more" in str(action):
            step = (int(value) / 100.0) if value else 0.10
            curr = endpoint.GetMasterVolumeLevelScalar()
            new_vol = min(1.0, curr + step)
            endpoint.SetMasterVolumeLevelScalar(new_vol, None)
            return f"Volume increased to {int(round(new_vol * 100))}%."
        elif "down" in str(action) or "dec" in str(action) or "less" in str(action):
            step = (int(value) / 100.0) if value else 0.10
            curr = endpoint.GetMasterVolumeLevelScalar()
            new_vol = max(0.0, curr - step)
            endpoint.SetMasterVolumeLevelScalar(new_vol, None)
            return f"Volume decreased to {int(round(new_vol * 100))}%."
    except Exception:
        pass

    # Keystroke fallback
    act_str = str(action).lower()
    if "up" in act_str or "inc" in act_str or "more" in act_str:
        for _ in range(5):
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
        return "Volume increased."
    elif "down" in act_str or "dec" in act_str or "less" in act_str:
        for _ in range(5):
            ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
        return "Volume decreased."
    elif "mute" in act_str:
        ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
        return "Volume mute toggled."
    return "Volume command executed."

_ACTIVE_TIMERS = []

def _automate_windows_clock(target_tab="stopwatch", auto_start=True, duration_mins=None):
    """
    Automates native Windows Clock via UIAutomation to switch to the exact tab
    (Stopwatch, Timer, Alarm) and click Start so timers/stopwatches actually run.
    """
    initialized_com = False
    try:
        import comtypes
        import comtypes.client
        import win32gui

        try:
            comtypes.CoInitialize()
            initialized_com = True
        except Exception:
            pass

        comtypes.client.GetModule("UIAutomationCore.dll")
        from comtypes.gen.UIAutomationClient import (
            CUIAutomation, IUIAutomation, TreeScope_Descendants,
            IUIAutomationInvokePattern, IUIAutomationSelectionItemPattern
        )

        user32 = ctypes.windll.user32
        try:
            hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

        uia = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)

        clock_hwnd = None
        for _ in range(25):
            def enum_cb(h, _):
                nonlocal clock_hwnd
                if win32gui.IsWindowVisible(h):
                    t = win32gui.GetWindowText(h)
                    c = win32gui.GetClassName(h)
                    if (c in ("ApplicationFrameWindow", "Windows.UI.Core.CoreWindow")) and ("clock" in t.lower() or "alarms" in t.lower()):
                        clock_hwnd = h
                        return False
                return True
            win32gui.EnumWindows(enum_cb, None)
            if clock_hwnd:
                break
            time.sleep(0.2)

        if not clock_hwnd:
            return

        elem = uia.ElementFromHandle(clock_hwnd)

        # Tab button Automation IDs in Windows 11 Clock
        btn_ids = {
            "stopwatch": "StopwatchButton",
            "timer": "TimerButton",
            "alarm": "AlarmButton",
            "clock": "ClockButton"
        }
        btn_id = btn_ids.get(target_tab, "StopwatchButton")

        cond_btn = uia.CreatePropertyCondition(30011, btn_id) # UIA_AutomationIdPropertyId
        tab_btn = elem.FindFirst(TreeScope_Descendants, cond_btn)
        if tab_btn:
            try:
                pattern = tab_btn.GetCurrentPattern(10010) # UIA_SelectionItemPatternId
                sel = pattern.QueryInterface(IUIAutomationSelectionItemPattern)
                sel.Select()
            except Exception:
                try:
                    pattern = tab_btn.GetCurrentPattern(10000) # UIA_InvokePatternId
                    inv = pattern.QueryInterface(IUIAutomationInvokePattern)
                    inv.Invoke()
                except Exception:
                    pass

        time.sleep(0.4)

        # Auto-start stopwatch or timer if requested
        if auto_start:
            if target_tab == "stopwatch":
                cond_start = uia.CreatePropertyCondition(30011, "StopwatchPlayPauseButton")
                start_btn = elem.FindFirst(TreeScope_Descendants, cond_start)
                if not start_btn:
                    cond_name = uia.CreatePropertyCondition(30005, "Start")
                    start_btn = elem.FindFirst(TreeScope_Descendants, cond_name)
                if start_btn:
                    try:
                        pattern = start_btn.GetCurrentPattern(10000)
                        inv = pattern.QueryInterface(IUIAutomationInvokePattern)
                        inv.Invoke()
                    except Exception:
                        pass
            elif target_tab == "timer" and duration_mins:
                # Look for matching timer tile play button
                cond_play = uia.CreatePropertyCondition(30011, "TimerPlayPauseButton")
                play_btns = elem.FindAll(TreeScope_Descendants, cond_play)
                if play_btns and play_btns.Length > 0:
                    idx = 0
                    if duration_mins <= 1: idx = 0
                    elif duration_mins <= 3: idx = 1
                    elif duration_mins <= 5: idx = 2
                    elif duration_mins <= 10: idx = 3
                    if idx < play_btns.Length:
                        target_btn = play_btns.GetElement(idx)
                        try:
                            pattern = target_btn.GetCurrentPattern(10000)
                            inv = pattern.QueryInterface(IUIAutomationInvokePattern)
                            inv.Invoke()
                        except Exception:
                            pass
    except Exception as e:
        print(f"⚠️ [Clock Automation Notice]: {e}")
    finally:
        if initialized_com:
            try:
                import comtypes
                comtypes.CoUninitialize()
            except Exception:
                pass

def clock_control(action="timer", duration_seconds=None, title=None):
    """
    Controls native Windows Clock app (Timer, Stopwatch, Alarm, World Clock).
    Actions:
    - 'timer': Opens Windows Clock Timer tab, auto-starts countdown, and schedules voice completion chime
    - 'stopwatch': Opens Windows Clock Stopwatch tab and immediately starts the stopwatch counting
    - 'alarm': Opens Windows Clock Alarm tab
    - 'clock': Opens Windows Clock app
    """
    act = (action or "clock").lower().strip()
    user32 = ctypes.windll.user32
    try:
        hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

    if "stopwatch" in act:
        subprocess.Popen(["explorer.exe", "ms-clock:"])
        threading.Thread(target=_automate_windows_clock, args=("stopwatch", True, None), daemon=True).start()
        return "Started Stopwatch in Windows Clock."
    elif "alarm" in act:
        subprocess.Popen(["explorer.exe", "ms-clock:"])
        threading.Thread(target=_automate_windows_clock, args=("alarm", False, None), daemon=True).start()
        return "Opened Alarms in Windows Clock."
    elif "timer" in act:
        subprocess.Popen(["explorer.exe", "ms-clock:"])
        mins = (float(duration_seconds) / 60.0) if (duration_seconds and float(duration_seconds) > 0) else None
        threading.Thread(target=_automate_windows_clock, args=("timer", True, mins), daemon=True).start()
        if duration_seconds and float(duration_seconds) > 0:
            secs = float(duration_seconds)
            mins_int = int(secs // 60)
            rem_secs = int(secs % 60)
            dur_str = f"{mins_int} minute{'s' if mins_int != 1 else ''}" if mins_int > 0 and rem_secs == 0 else f"{int(secs)} seconds"

            def _timer_worker():
                time.sleep(secs)
                try:
                    import winsound
                    for _ in range(3):
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                        time.sleep(0.4)
                except Exception:
                    pass
            th = threading.Thread(target=_timer_worker, daemon=True)
            th.start()
            _ACTIVE_TIMERS.append(th)
            return f"Started a {dur_str} timer in Windows Clock."
        return "Opened Timer in Windows Clock."
    else:
        subprocess.Popen(["explorer.exe", "ms-clock:"])
        return "Opened Windows Clock."

def get_installed_games():
    """Finds all games installed on this computer (Steam, Epic, Desktop shortcuts, Registry)."""
    games = set()
    # 1. Steam Common folder
    steam_dirs = [
        r"C:\Program Files (x86)\Steam\steamapps\common",
        r"C:\Program Files\Steam\steamapps\common",
        r"D:\SteamLibrary\steamapps\common",
        r"E:\SteamLibrary\steamapps\common",
    ]
    for s_dir in steam_dirs:
        if os.path.exists(s_dir):
            for f in os.listdir(s_dir):
                if os.path.isdir(os.path.join(s_dir, f)) and f.lower() not in ["steamworks shared", "steam controller configs"]:
                    games.add(f)

    # 2. Desktop shortcuts
    for d in [os.path.expanduser("~/Desktop"), r"C:\Users\Public\Desktop"]:
        if os.path.exists(d):
            for f in os.listdir(d):
                name_clean = f.replace(".lnk", "").replace(".url", "").strip()
                if any(k in name_clean.lower() for k in [
                    "roblox", "counter-strike", "cs", "forza", "gta", "valorant", "minecraft",
                    "steam", "game", "epic", "riot", "rdr", "red dead", "battlefield", "pubg",
                    "delta force", "goose", "arc raiders", "efootball", "yu-gi-oh", "beyond-all-reason"
                ]):
                    if not name_clean.lower().startswith("steam") and "controller" not in name_clean.lower():
                        games.add(name_clean)

    # 3. Windows Registry
    try:
        import winreg
        keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for root, sub in keys:
            try:
                with winreg.OpenKey(root, sub) as k:
                    for i in range(winreg.QueryInfoKey(k)[0]):
                        try:
                            subname = winreg.EnumKey(k, i)
                            with winreg.OpenKey(k, subname) as appkey:
                                name, _ = winreg.QueryValueEx(appkey, "DisplayName")
                                if any(g in name.lower() for g in [
                                    "counter-strike", "forza", "roblox", "battlefield", "pubg",
                                    "red dead", "delta force", "beyond-all-reason", "minecraft",
                                    "untitled goose", "arc raiders", "efootball", "yu-gi-oh"
                                ]):
                                    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', name).strip()
                                    games.add(clean)
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass

    game_list = sorted(list(games))
    if not game_list:
        return ["Counter-Strike 2", "Roblox", "Forza Horizon 6"]
    return game_list

def move_item(source_path, dest_path):
    """Moves a file or folder from source to destination."""
    src = os.path.expanduser(source_path.strip().strip("'\""))
    dst = os.path.expanduser(dest_path.strip().strip("'\""))
    if not os.path.exists(src):
        return f"Source path does not exist: {src}"
    try:
        shutil.move(src, dst)
        return f"Moved successfully from {src} to {dst}"
    except Exception as e:
        return f"Failed to move item: {e}"

def resolve_folder_path(folder_name=""):
    """Resolves friendly folder names like 'work', 'downloads', 'desktop' or absolute paths."""
    raw = (folder_name or "").strip().strip("'\"").lower()
    user_home = os.path.expanduser("~")

    # 1. Direct standard aliases
    if "download" in raw:
        return os.path.join(user_home, "Downloads"), "Downloads"
    elif "desktop" in raw:
        return os.path.join(user_home, "Desktop"), "Desktop"
    elif "document" in raw:
        return os.path.join(user_home, "Documents"), "Documents"
    elif "picture" in raw or "photo" in raw:
        return os.path.join(user_home, "Pictures"), "Pictures"
    elif "screenshot" in raw:
        ss_dir = os.path.join(user_home, "Pictures", "Screenshots")
        return (ss_dir if os.path.exists(ss_dir) else os.path.join(user_home, "Pictures")), "Screenshots"
    elif "music" in raw:
        return os.path.join(user_home, "Music"), "Music"
    elif "video" in raw:
        return os.path.join(user_home, "Videos"), "Videos"
    elif "project" in raw or "repo" in raw:
        return os.getcwd(), "Current Project"

    # 2. Work / Workspace folder smart resolution (C:\work, D:\work, ~/work, etc.)
    if any(k in raw for k in ["work", "workspace"]):
        work_candidates = [
            r"C:\work",
            r"D:\work",
            os.path.join(user_home, "work"),
            os.path.join(user_home, "workspace"),
            r"C:\workspace",
            os.path.join(user_home, "Desktop", "work"),
            os.path.join(user_home, "Downloads", "work"),
            os.getcwd()
        ]
        for candidate in work_candidates:
            if os.path.exists(candidate):
                return candidate, "Work"

    # 2b. Game & AppData directory resolution (Minecraft, TLauncher, .minecraft, .tlauncher)
    appdata_roaming = os.environ.get("APPDATA", os.path.join(user_home, "AppData", "Roaming"))
    appdata_local = os.environ.get("LOCALAPPDATA", os.path.join(user_home, "AppData", "Local"))
    if "minecraft" in raw or "tlauncher" in raw:
        game_candidates = [
            os.path.join(appdata_roaming, ".minecraft"),
            os.path.join(appdata_roaming, ".tlauncher"),
            os.path.join(user_home, ".minecraft"),
            os.path.join(user_home, ".tlauncher"),
            os.path.join(appdata_roaming, "Minecraft"),
            os.path.join(appdata_local, "Minecraft"),
        ]
        if "tlauncher" in raw:
            game_candidates.insert(0, os.path.join(appdata_roaming, ".tlauncher"))
        for gc in game_candidates:
            if os.path.exists(gc):
                title = "TLauncher" if "tlauncher" in os.path.basename(gc).lower() else "Minecraft"
                return gc, title

    # 3. Direct absolute or user path
    if folder_name:
        p = os.path.expanduser(folder_name.strip("'\""))
        if os.path.exists(p):
            return p, os.path.basename(p) or p

    # 4. Search top-level user directories, root drives, and AppData for a matching folder name
    clean_target = re.sub(r'\b(folder|dir|directory)\b', '', raw).strip()
    clean_target_no_spaces = clean_target.replace(" ", "")
    if clean_target:
        search_bases = [
            r"C:\\", r"D:\\", user_home,
            os.path.join(user_home, "Desktop"),
            os.path.join(user_home, "Downloads"),
            appdata_roaming,
            appdata_local
        ]
        for base in search_bases:
            if os.path.exists(base):
                try:
                    for entry in os.listdir(base):
                        entry_lower = entry.lower()
                        if (entry_lower == clean_target or
                            entry_lower == f".{clean_target}" or
                            entry_lower.replace(" ", "") == clean_target_no_spaces or
                            entry_lower.replace(" ", "") == f".{clean_target_no_spaces}"):
                            p = os.path.join(base, entry)
                            if os.path.isdir(p):
                                return p, entry.lstrip(".")
                except Exception:
                    pass

    return os.path.join(user_home, "Downloads"), "Downloads"

def open_folder(folder_path=""):
    """Opens a folder in Windows File Explorer with intelligent resolution."""
    p, display_name = resolve_folder_path(folder_path)
    if not os.path.exists(p):
        return f"Folder does not exist: {p}"
    subprocess.Popen(["explorer.exe", os.path.normpath(p)])
    return f"Opened {display_name} folder ({p})."

def open_last_screenshot():
    """Finds and opens the most recent screenshot taken on the computer."""
    user_home = os.path.expanduser("~")
    search_dirs = [
        os.path.join(user_home, "Pictures", "Screenshots"),
        os.path.join(user_home, "Pictures"),
        os.path.join(user_home, "Desktop")
    ]
    candidates = []
    for d in search_dirs:
        if os.path.exists(d):
            try:
                for f in os.listdir(d):
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                        fp = os.path.join(d, f)
                        try:
                            candidates.append((fp, os.path.getmtime(fp)))
                        except Exception:
                            pass
            except Exception:
                pass

    if not candidates:
        return "No recent screenshots found in Pictures or Desktop."

    candidates.sort(key=lambda x: x[1], reverse=True)
    latest_file = candidates[0][0]
    try:
        os.startfile(latest_file)
        return f"Opened latest screenshot: {os.path.basename(latest_file)}."
    except Exception as e:
        return f"Found screenshot {latest_file} but failed to open: {e}"

def get_system_health():
    """
    Hardware Telemetry & Top Resource Monitor:
    Returns CPU, RAM, GPU, VRAM and top resource-consuming processes.
    """
    import psutil
    cpu_pct = int(psutil.cpu_percent(interval=0.1))
    mem = psutil.virtual_memory()
    ram_pct = int(mem.percent)
    ram_used_gb = mem.used / (1024 ** 3)
    ram_total_gb = mem.total / (1024 ** 3)

    gpu_str = ""
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu_name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(gpu_name, bytes):
            gpu_name = gpu_name.decode("utf-8")
        gpu_util = int(pynvml.nvmlDeviceGetUtilizationRates(handle).gpu)
        vram = pynvml.nvmlDeviceGetMemoryInfo(handle)
        vram_used_gb = vram.used / (1024 ** 3)
        vram_total_gb = vram.total / (1024 ** 3)
        gpu_str = f"GPU is at {gpu_util}% ({vram_used_gb:.1f} of {vram_total_gb:.1f} GB VRAM). "
    except Exception:
        pass

    # Aggregate processes by executable name
    proc_map = {}
    for p in psutil.process_iter(['name', 'memory_info']):
        try:
            info = p.info
            name = (info.get('name') or '').strip()
            if not name or name.lower() in ('system idle process', 'system', 'registry', 'memcompression'):
                continue
            mem_mb = (info['memory_info'].rss if info.get('memory_info') else 0) / (1024 * 1024)
            if mem_mb > 30:
                stem = name.replace('.exe', '').lower()
                if stem in proc_map:
                    proc_map[stem]['mem'] += mem_mb
                    proc_map[stem]['count'] += 1
                else:
                    proc_map[stem] = {'mem': mem_mb, 'count': 1, 'name': name.replace('.exe', '')}
        except Exception:
            continue

    sorted_procs = sorted(proc_map.values(), key=lambda x: x['mem'], reverse=True)
    top_items = []
    for p in sorted_procs[:3]:
        if p['count'] > 1:
            top_items.append(f"{p['name']} ({int(p['mem'])} MB across {p['count']} instances)")
        else:
            top_items.append(f"{p['name']} ({int(p['mem'])} MB)")

    net_str = ""
    try:
        net1 = psutil.net_io_counters()
        time.sleep(0.08)
        net2 = psutil.net_io_counters()
        up_kb = (net2.bytes_sent - net1.bytes_sent) / (1024 * 0.08)
        down_kb = (net2.bytes_recv - net1.bytes_recv) / (1024 * 0.08)
        net_str = f"Network LAN: upload is {up_kb:.1f} KB/s, download is {down_kb:.1f} KB/s. "
    except Exception:
        pass

    top_str = ", ".join(top_items) if top_items else "no heavy processes"
    speech = (
        f"CPU is at {cpu_pct}%, RAM is at {ram_pct}% ({ram_used_gb:.1f} of {ram_total_gb:.1f} GB). "
        f"{gpu_str}{net_str}Top apps consuming the most memory are {top_str}. "
        f"Say 'end' followed by the app name if you want me to terminate any of them."
    )
    return speech

def web_search(query):
    """Searches the live web for recent information, models, news, and facts."""
    import html as html_lib
    clean_q = (query or "").strip().strip("'\"")
    if not clean_q:
        return "Please provide a search query."

    # 0. DuckDuckGo Instant Answer API (Sub-200ms clean encyclopedic abstract)
    try:
        ddg_api_url = "https://api.duckduckgo.com/?q=" + urllib.parse.quote(clean_q) + "&format=json&no_html=1&skip_disambig=1"
        req_api = urllib.request.Request(ddg_api_url, headers={"User-Agent": "JarvisAssistant/1.0"})
        with urllib.request.urlopen(req_api, timeout=4) as resp_api:
            ddg_data = json.loads(resp_api.read().decode("utf-8"))
        abstract = (ddg_data.get("AbstractText") or "").strip()
        if abstract:
            return f"- {abstract}"
    except Exception:
        pass

    # 1. DuckDuckGo HTML Search
    try:
        ddg_url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(clean_q)
        req = urllib.request.Request(ddg_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })
        with urllib.request.urlopen(req, timeout=6) as resp:
            html_text = resp.read().decode("utf-8", errors="ignore")
        snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', html_text)
        if not snippets:
            snippets = re.findall(r'<td class="result-snippet"[^>]*>(.*?)</td>', html_text)
        clean = [html_lib.unescape(re.sub(r'<[^>]+>', '', s).strip()) for s in snippets if s.strip()]
        if clean:
            return "\n".join([f"- {c}" for c in clean[:4]])
    except Exception:
        pass

    # 2. Bing Search Fallback
    try:
        url = "https://www.bing.com/search?q=" + urllib.parse.quote(clean_q)
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        snippets = re.findall(r'<p class="b_lineclamp[^"]*"[^>]*>(.*?)</p>', html)
        clean = [html_lib.unescape(re.sub(r'<[^>]+>', '', s).strip()) for s in snippets[:4] if s.strip()]
        if clean:
            return "\n".join([f"- {c}" for c in clean])
    except Exception:
        pass

    # 3. Wikipedia OpenSearch Fallback
    try:
        search_api = "https://en.wikipedia.org/w/api.php?action=opensearch&format=json&limit=1&search=" + urllib.parse.quote(clean_q)
        req = urllib.request.Request(search_api, headers={"User-Agent": "JarvisAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if len(data) > 1 and data[1]:
            best_title = data[1][0]
            summary_api = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(best_title)
            req2 = urllib.request.Request(summary_api, headers={"User-Agent": "JarvisAssistant/1.0"})
            with urllib.request.urlopen(req2, timeout=4) as resp2:
                sdata = json.loads(resp2.read().decode("utf-8"))
            if sdata.get("extract"):
                return f"- {sdata.get('extract')}"
    except Exception:
        pass

    return f"No quick web results found for '{clean_q}'."

def create_folder(folder_path=""):
    """Creates a new folder or directory."""
    raw = (folder_path or "").strip().strip("'\"")
    if not raw:
        return "Please specify a folder name or path to create."
    p = os.path.expanduser(raw)
    if not os.path.isabs(p):
        p = os.path.join(os.path.expanduser("~"), "Downloads", raw)
    try:
        os.makedirs(p, exist_ok=True)
        return f"Created folder '{os.path.basename(p)}' at {p}."
    except Exception as e:
        return f"Failed to create folder: {e}"

def organize_folder(folder_name="downloads"):
    """Automatically sorts and arranges loose files in a folder into categorized subfolders."""
    target_dir, display_name = resolve_folder_path(folder_name)
    if not os.path.exists(target_dir):
        return f"Directory does not exist: {target_dir}"

    categories = {
        "Images": {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff', '.raw'},
        "Videos": {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'},
        "Audio": {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus'},
        "Documents": {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.txt', '.csv', '.rtf', '.epub', '.md'},
        "Archives": {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.iso', '.torrent'},
        "Installers": {'.exe', '.msi', '.dmg', '.apk', '.bat', '.cmd'},
        "3D & Creative": {'.blend', '.fbx', '.obj', '.stl', '.dae', '.psd', '.ai', '.kra', '.blend1'},
        "Code": {'.py', '.json', '.xml', '.yaml', '.yml', '.html', '.css', '.js', '.ts', '.cpp', '.c', '.h', '.java', '.sql', '.rs', '.go'},
    }

    ext_to_cat = {}
    for cat, exts in categories.items():
        for ext in exts:
            ext_to_cat[ext.lower()] = cat

    try:
        loose_files = []
        for item in os.listdir(target_dir):
            if item.startswith(".") or item.startswith("$") or item.lower() in ("desktop.ini", "thumbs.db"):
                continue
            full_item_path = os.path.join(target_dir, item)
            if os.path.isfile(full_item_path):
                loose_files.append(item)
    except Exception as e:
        return f"Error reading folder {target_dir}: {e}"

    if not loose_files:
        return f"No loose files found to organize in {display_name}. Everything is already organized into folders."

    moved_counts = {}
    for filename in loose_files:
        _, ext = os.path.splitext(filename)
        ext_lower = ext.lower()
        cat = ext_to_cat.get(ext_lower, "Other")

        cat_dir = os.path.join(target_dir, cat)
        try:
            os.makedirs(cat_dir, exist_ok=True)
            src_path = os.path.join(target_dir, filename)
            dest_path = os.path.join(cat_dir, filename)

            if os.path.exists(dest_path):
                base_name, file_ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(os.path.join(cat_dir, f"{base_name}_{counter}{file_ext}")):
                    counter += 1
                dest_path = os.path.join(cat_dir, f"{base_name}_{counter}{file_ext}")

            shutil.move(src_path, dest_path)
            moved_counts[cat] = moved_counts.get(cat, 0) + 1
        except Exception as e:
            print(f"[Warning] Failed moving {filename}: {e}")

    total_moved = sum(moved_counts.values())
    if total_moved == 0:
        return f"No files were moved in {display_name}."

    breakdown = ", ".join([f"{cnt} {cat}" for cat, cnt in sorted(moved_counts.items(), key=lambda x: -x[1])])
    return f"Organized {total_moved} files in {display_name} into folders: {breakdown}."

def execute_command(command):
    """Runs a shell CLI command and returns output."""
    cmd = command.strip().strip("'\"")
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=12)
        out = (res.stdout + "\n" + res.stderr).strip()
        return out if out else "(Command executed successfully with no output)"
    except Exception as e:
        return f"Error executing command: {e}"

def list_folder_contents(folder_name="", max_items=15):
    """Lists files and folders inside common directories or a specified directory."""
    raw = (folder_name or "").strip().strip("'\"").lower()
    user_home = os.path.expanduser("~")
    
    if "download" in raw:
        target_dir = os.path.join(user_home, "Downloads")
        display_name = "Downloads"
    elif "desktop" in raw:
        target_dir = os.path.join(user_home, "Desktop")
        display_name = "Desktop"
    elif "document" in raw:
        target_dir = os.path.join(user_home, "Documents")
        display_name = "Documents"
    elif "picture" in raw or "photo" in raw:
        target_dir = os.path.join(user_home, "Pictures")
        display_name = "Pictures"
    elif "project" in raw or "code" in raw or "repo" in raw:
        target_dir = os.getcwd()
        display_name = "Current Project"
    elif folder_name and os.path.exists(os.path.expanduser(folder_name.strip("'\""))):
        target_dir = os.path.expanduser(folder_name.strip("'\""))
        display_name = target_dir
    else:
        target_dir = os.path.join(user_home, "Downloads")
        display_name = "Downloads"

    if not os.path.exists(target_dir):
        return f"Directory does not exist: {target_dir}"

    try:
        entries = []
        for item in os.listdir(target_dir):
            if item.startswith(".") or item.startswith("$"):
                continue
            full_path = os.path.join(target_dir, item)
            is_dir = os.path.isdir(full_path)
            try:
                mtime = os.path.getmtime(full_path)
                size_mb = os.path.getsize(full_path) / (1024 * 1024) if not is_dir else 0
                entries.append((item, is_dir, mtime, size_mb))
            except Exception:
                entries.append((item, is_dir, 0, 0))

        # Sort by modification time descending (most recent first)
        entries.sort(key=lambda x: x[2], reverse=True)
        
        lines = [f"Contents of {display_name} ({len(entries)} items total):"]
        for name, is_dir, mtime, size_mb in entries[:max_items]:
            kind = "[DIR] " if is_dir else "      "
            size_str = f"({size_mb:.1f} MB)" if not is_dir and size_mb >= 0.1 else ""
            lines.append(f"  {kind}{name} {size_str}".rstrip())
            
        if len(entries) > max_items:
            lines.append(f"  ... and {len(entries) - max_items} more items")
            
        return "\n".join(lines)
    except Exception as e:
        return f"Error reading folder {target_dir}: {e}"

def search_local_files(query, directory=None):
    """Searches for files matching query in local user and project directories."""
    q = query.strip().strip("'\"").lower()
    user_home = os.path.expanduser("~")
    
    if directory:
        search_dirs = [os.path.expanduser(directory.strip().strip("'\""))]
    else:
        # Check high-value user directories first for near-instant results
        search_dirs = [
            os.getcwd(),
            os.path.join(user_home, "Downloads"),
            os.path.join(user_home, "Desktop"),
            os.path.join(user_home, "Documents"),
            os.path.join(user_home, "Pictures")
        ]

    matches = []
    for base in search_dirs:
        if not os.path.exists(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["node_modules", "AppData", "__pycache__", "venv", ".cache"]]
            for f in files:
                if q in f.lower():
                    matches.append(os.path.join(root, f))
                    if len(matches) >= 10:
                        break
            if len(matches) >= 10:
                break
        if len(matches) >= 10:
            break

    if not matches:
        return f"No files matching '{query}' found in common directories."
    return "\n".join(matches)

def read_file_content(file_path):
    """Reads the contents of a local file."""
    p = os.path.expanduser(file_path.strip().strip("'\""))
    if not os.path.exists(p):
        cwd_p = os.path.join(os.getcwd(), p)
        if os.path.exists(cwd_p):
            p = cwd_p
        else:
            matches = search_local_files(os.path.basename(p))
            first_match = matches.split("\n")[0] if matches and not matches.startswith("No files") else None
            if first_match and os.path.exists(first_match):
                p = first_match
            else:
                return f"File does not exist: {file_path}"
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            preview = "".join(lines[:100])
            if len(lines) > 100:
                preview += f"\n...(truncated, {len(lines)} total lines)"
            return preview
    except Exception as e:
        return f"Error reading file: {e}"

AVAILABLE_TOOLS = {
    "open_url": open_url,
    "play_video": play_video,
    "play_youtube": play_video,
    "open_leetcode": open_leetcode,
    "open_app": open_app,
    "close_app": close_app,
    "take_screenshot": take_screenshot,
    "inspect_screen": inspect_screen,
    "see_screen": inspect_screen,
    "read_screen": inspect_screen,
    "adjust_brightness": adjust_brightness,
    "adjust_volume": adjust_volume,
    "get_installed_games": get_installed_games,
    "open_folder": open_folder,
    "create_folder": create_folder,
    "organize_folder": organize_folder,
    "list_folder": list_folder_contents,
    "list_folder_contents": list_folder_contents,
    "search_files": search_local_files,
    "search_local_files": search_local_files,
    "read_file": read_file_content,
    "read_file_content": read_file_content,
    "move_item": move_item,
    "run_command": execute_command,
    "browser_control": browser_control,
    "open_last_screenshot": open_last_screenshot,
    "get_system_health": get_system_health,
    "web_search": web_search
}

def parse_and_execute_tool(text):
    """
    Looks for <<TOOL: name(...)>> in the text, executes it,
    and returns (tool_found, execution_message, cleaned_text).
    """
    pattern = r'<<TOOL:\s*([a-zA-Z0-9_]+)\((.*?)\)\s*>>'
    matches = list(re.finditer(pattern, text))
    if not matches:
        return False, None, text

    messages = []
    for match in matches:
        func_name = match.group(1).strip()
        raw_args = match.group(2).strip()

        if func_name in AVAILABLE_TOOLS:
            func = AVAILABLE_TOOLS[func_name]
            try:
                parsed_call = ast.parse(f"func({raw_args})").body[0].value
                args = [ast.literal_eval(a) for a in parsed_call.args]
                kwargs = {k.arg: ast.literal_eval(k.value) for k in parsed_call.keywords}
                res = func(*args, **kwargs)
                if isinstance(res, tuple):
                    res = res[0]
                elif isinstance(res, list):
                    res = ", ".join(res)
                messages.append(f"[Action: {res}]")
            except Exception:
                try:
                    arg_clean = raw_args.strip("'\"")
                    res = func(arg_clean) if arg_clean else func()
                    if isinstance(res, tuple):
                        res = res[0]
                    elif isinstance(res, list):
                        res = ", ".join(res)
                    messages.append(f"[Action: {res}]")
                except Exception as e:
                    messages.append(f"[Tool Error ({func_name}): {e}]")
        else:
            messages.append(f"[Tool Error: Unrecognized tool '{func_name}']")

    cleaned_text = re.sub(pattern, '', text).strip()
    return True, "\n".join(messages), cleaned_text

def detect_and_run_intent(text):
    """
    Directly inspects the user message for explicit tool and action requests
    (screen vision, games, brightness, volume, YouTube, LeetCode, software, screenshots, CLI, folders)
    and executes them immediately without relying solely on LLM tag generation.
    Returns (handled: bool, action_msg: str, response_speech: str, needs_llm_analysis: bool).
    """
    t = text.lower().strip()

    # Browser preference (default: Helium)
    browser = None
    if "helium" in t:
        browser = "helium"
    elif "firefox" in t:
        browser = "firefox"
    elif "chrome" in t:
        browser = "chrome"
    else:
        browser = "helium"

    # 1. Vision / Screen Reading Intent ("Look at my screen", "What's on my screen")
    if any(p in t for p in ["look at my screen", "what is on my screen", "what's on my screen", "can you see my screen", "read my screen", "inspect my screen", "see my screen", "look at screen", "read the screen", "check my screen"]):
        screen_text = inspect_screen()
        lines = [l for l in screen_text.split("\n") if l.strip()]
        preview = " | ".join(lines[:3]) if lines else "Empty"
        if len(preview) > 100: preview = preview[:97] + "..."
        action_msg = f"[Action: Screen analyzed via Windows OCR ({len(lines)} lines detected: {preview})]"
        speech = "I have captured and read your screen. Let me analyze it for you."
        return True, action_msg, speech, True # Send to LLM with screen content

    # 2. Installed Games Intent ("What are the games I have in my computer?", "list my games")
    if any(k in t for k in ["games", "game installed", "installed games", "games i have", "my games", "what games"]):
        games = get_installed_games()
        preview = ", ".join(games[:8]) + (f" and {len(games)-8} more" if len(games) > 8 else "")
        action_msg = f"[Action: Found {len(games)} games installed on this computer: {', '.join(games)}]"
        speech = f"You have several games installed on your laptop, including {preview}."
        return True, action_msg, speech, False

    # 3. Brightness Control ("Can you increase the brightness?", "Set brightness to 80")
    if "brightness" in t:
        action = "increase"
        val = None
        if any(w in t for w in ["increase", "up", "more", "raise", "high", "brighten"]):
            action = "increase"
        elif any(w in t for w in ["decrease", "down", "lower", "less", "dim", "reduce"]):
            action = "decrease"
        m = re.search(r'(\d+)', t)
        if m:
            action = "set"
            val = int(m.group(1))
        res = adjust_brightness(action, val)
        return True, f"[Action: {res}]", res, False

    # 4. Volume Control ("Increase the volume", "mute", "set volume to 50", "sound to 50")
    if "volume" in t or "sound" in t:
        m = re.search(r'(\d+)', t)
        if m and any(w in t for w in ["set", "to", "at", "%", "sound"]):
            val = int(m.group(1))
            res = adjust_volume("set", val)
            return True, f"[Action: {res}]", f"Set volume to {val} percent for you.", False
        elif any(w in t for w in ["increase", "up", "more", "raise", "loud", "louder"]):
            res = adjust_volume("increase")
            return True, f"[Action: {res}]", "Increased volume for you.", False
        elif any(w in t for w in ["decrease", "down", "lower", "less", "quiet", "softer"]):
            res = adjust_volume("decrease")
            return True, f"[Action: {res}]", "Decreased volume for you.", False
        elif "mute" in t:
            res = adjust_volume("mute")
            return True, f"[Action: {res}]", "Toggled volume mute for you.", False

    # 4c. Windows Clock, Timer, Stopwatch & Alarm Intent
    # e.g. "set five minutes stopwatch", "start stopwatch", "open stopwatch", "set a timer for 5 minutes", "5 minute timer", "set alarm"
    has_stopwatch = any(k in t for k in ["stopwatch", "stop watch"])
    has_timer = any(k in t for k in ["timer", "countdown"])
    has_alarm = any(k in t for k in ["alarm", "alarms"])
    has_clock = any(k in t for k in ["clock", "open clock", "launch clock"]) and not (has_stopwatch or has_timer or has_alarm)

    if has_stopwatch or has_timer or has_alarm or has_clock:
        # Extract duration if present: e.g. "5 minutes", "30 seconds", "1 hour"
        m_m = re.search(r'(\d+)\s*(?:min|minute|minutes|m\b)', t)
        m_s = re.search(r'(\d+)\s*(?:sec|second|seconds|s\b)', t)
        m_h = re.search(r'(\d+)\s*(?:hour|hours|hr|hrs\b)', t)

        tot_secs = 0
        if m_h:
            tot_secs += int(m_h.group(1)) * 3600
        if m_m:
            tot_secs += int(m_m.group(1)) * 60
        if m_s:
            tot_secs += int(m_s.group(1))

        if not (m_h or m_m or m_s):
            m_num = re.search(r'\b(?:set|for|sit)\s+(\d+)\b', t)
            if m_num:
                tot_secs = int(m_num.group(1)) * 60

        dur_sec = tot_secs if tot_secs > 0 else None
        dur_label = f"{dur_sec // 60} minute" if (dur_sec and dur_sec >= 60) else (f"{dur_sec} second" if dur_sec else "")

        if has_stopwatch:
            res = clock_control("stopwatch", duration_seconds=dur_sec)
            speech = "Starting the Stopwatch in Windows Clock for you."
            return True, f"[Action: {res}]", speech, False
        elif has_timer:
            res = clock_control("timer", duration_seconds=dur_sec)
            speech = f"Opening Windows Clock and starting a {dur_label} timer for you." if dur_sec else "Opening the Timer in Windows Clock for you."
            return True, f"[Action: {res}]", speech, False
        elif has_alarm:
            res = clock_control("alarm")
            speech = "Opening Alarms in Windows Clock for you."
            return True, f"[Action: {res}]", speech, False
        elif has_clock:
            res = clock_control("clock")
            speech = "Opening Windows Clock for you."
            return True, f"[Action: {res}]", speech, False

    # 4b. Browser Tab & Playback Control ("play it", "it is not playing", "resume", "pause", "next tab", "previous tab", "close tab", "what is the url")
    if any(p in t for p in ["it is not playing", "it's not playing", "not playing", "play the song", "play it", "resume the video", "pause the video", "pause the song", "resume playback", "toggle play"]):
        res = browser_control("play_pause")
        return True, f"[Action: {res}]", res, False

    if any(p in t for p in ["next tab", "switch to next tab", "go to next tab"]):
        res = browser_control("next_tab")
        return True, f"[Action: {res}]", res, False

    if any(p in t for p in ["previous tab", "prev tab", "switch to previous tab", "go to previous tab"]):
        res = browser_control("previous_tab")
        return True, f"[Action: {res}]", res, False

    if any(p in t for p in ["close this tab", "close the tab", "close active tab", "close tab"]):
        res = browser_control("close_tab")
        return True, f"[Action: {res}]", res, False

    if any(p in t for p in ["reopen tab", "undo close tab", "reopen closed tab"]):
        res = browser_control("reopen_tab")
        return True, f"[Action: {res}]", res, False

    if any(p in t for p in ["what is the url", "what's the url", "get url", "current url", "copy url", "read url"]):
        res = browser_control("get_url")
        return True, f"[Action: {res}]", res, False

    # 5. YouTube Intent (clean extraction, conversational filler stripping, direct playback vs search)
    is_play_music = t.startswith("play ") and any(w in t for w in ["music", "song", "theme", "track", "audio", "video", "ost", "lofi", "beats", "remix"])
    if ("youtube" in t and any(w in t for w in ["open", "play", "launch", "start", "show", "watch", "want", "search", "find", "video", "tutorial"])) or is_play_music:
        clean = re.sub(r'^(hey\s+jarvis\s*,?\s*|jarvis\s*,?\s*)', '', t)
        # Strip conversational fillers
        fillers = [
            r'\buh\b', r'\bum\b', r'\byou know\b', r'\bi mean\b', r'\bi told you that\b',
            r'\bi told told you that\b', r'\blike\b', r'\bso\b', r'\bactually\b'
        ]
        norm = clean
        for f in fillers:
            norm = re.sub(f, '', norm)
        norm = re.sub(r'\s+', ' ', norm).strip()

        # Phonetic & mishearing normalizations
        norm = re.sub(r'\bas a bigger\b', 'for beginners', norm)
        norm = re.sub(r'\bbigger\b', 'beginner', norm)
        norm = re.sub(r'\blanding numpy\b', 'learning numpy', norm)
        norm = re.sub(r'\bra expect sell\b', 'array except self', norm)
        norm = re.sub(r'\bproduct of ra\b', 'product of array', norm)
        norm = re.sub(r'\bexpensive\s+(?:lead\s*code|leetcode)\b', 'except self leetcode', norm)
        norm = re.sub(r'\b(?:expensive|expect\s+sell)\b', 'except self', norm)
        norm = re.sub(r'\blead code\b', 'leetcode', norm)

        # Check for explicit homepage requests
        is_homepage_request = norm in [
            "open youtube", "open the youtube", "launch youtube", "go to youtube",
            "youtube", "open youtube homepage", "youtube homepage"
        ]
        if is_homepage_request:
            res = open_url("https://www.youtube.com", browser=browser)
            speech = f"Opening YouTube in {browser.title()} for you." if browser else "Opening YouTube for you."
            return True, f"[Action: {res}]", speech, False

        # Extract search or playback query
        # 1. "open/play/show/watch X on/in youtube"
        m = re.search(r'(?:i\s+want\s+(?:you\s+to\s+)?|can\s+you\s+)?(?:open|play|show|watch|find|get)\s+(.+?)\s+(?:on|in)\s+youtube', norm)
        if not m:
            m = re.search(r'play\s+(.+?)(?:\s+on|\s+in)?\s+youtube', norm)
        if not m:
            m = re.search(r'(?:search\s+(?:on\s+)?youtube\s+for|youtube\s+search\s+(?:for\s+)?)(.+)', norm)
        if not m:
            m = re.search(r'open\s+youtube(?:\s+(?:and|to)\s+(?:search|play))?\s+(.+)', norm)
        if not m:
            # e.g. "i want a [best] [youtube] video [where/to/for/about] X"
            m = re.search(r'(?:want|find|show|watch|get|give me|look for)\s+(?:a\s+|the\s+)?(?:best\s+|good\s+)?(?:youtube\s+video|video\s+on\s+youtube|video|tutorial)\s+(?:where\s+i\s+can\s+|where\s+|to\s+|for\s+|about\s+|on\s+|how\s+to\s+)?(.+)', norm)
        if not m:
            # e.g. "youtube video [where/to/for/about] X"
            m = re.search(r'(?:youtube\s+video|video\s+on\s+youtube)\s+(?:where\s+i\s+can\s+|where\s+|to\s+|for\s+|about\s+|on\s+|how\s+to\s+)?(.+)', norm)
        if not m and is_play_music:
            m = re.search(r'play\s+(.+)', norm)

        query = m.group(1).strip() if m else ""
        query = re.sub(r'\b(in\s+my\s+browser|in\s+browser|in\s+helium|in\s+firefox|in\s+chrome|please|for\s+me|tab|video|videos)\b', '', query).strip()
        query = re.sub(r'^(for|about|with|the)\s+', '', query).strip()
        query = query.strip('\'".,?! ')

        if query and query not in ["", "homepage", "app", "site", "website", "something", "a video", "any video", "videos"]:
            if any(w in t for w in ["play", "watch", "listen", "song", "music", "theme", "track", "lofi", "video", "tutorial", "want", "learn"]):
                res = play_video(query, browser=browser)
                speech = f"Playing '{query}' on YouTube."
                return True, f"[Action: {res}]", speech, False
            else:
                target = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                res = open_url(target, browser=browser)
                speech = f"Searching YouTube for {query}."
                return True, f"[Action: Opened YouTube search for '{query}' ({target})]", speech, False
        elif any(p in t for p in ["open youtube", "launch youtube", "go to youtube", "open the youtube"]):
            res = open_url("https://www.youtube.com", browser=browser)
            speech = f"Opening YouTube in {browser.title()} for you." if browser else "Opening YouTube for you."
            return True, f"[Action: {res}]", speech, False

    # 6. LeetCode Intent (smart GraphQL daily resolver, slug verification, frank fallback)
    if "leetcode" in t and any(w in t for w in ["open", "show", "go to", "solve", "want", "do", "find", "challenge"]):
        action, speech = open_leetcode(t, browser=browser)
        return True, f"[Action: {action}]", speech, False

    # 7. System Files Permission / Access Confirmation
    if any(p in t for p in [
        "access to system files", "access to files", "access system files", "access my files",
        "can you access my files", "can you see my files", "why no access to system files",
        "why this model has no access to system files", "do you have access to local files",
        "do you have access to system files", "have access to files"
    ]):
        speech = "I do have direct access to your local system files, directories, and documents. I can search for files, read code, list folders like Downloads or Desktop, and execute terminal commands for you."
        action = "[Action: Confirmed full local file system access (search_files, read_file, list_folder_contents, open_folder, move_item, run_command)]"
        return True, action, speech, False

    # 8. List Folder Contents ("what files are in downloads", "list files in desktop")
    if any(w in t for w in ["what files", "list files", "show files", "what's in", "whats in", "what do i have in"]) and any(f in t for f in ["download", "desktop", "document", "picture", "folder", "project"]):
        m = re.search(r'(?:in|of)\s+([a-zA-Z0-9_\-\\/\s]+)', t)
        target = m.group(1).strip() if m else "downloads"
        res = list_folder_contents(target, max_items=12)
        preview_speech = f"Here are the files in your {target.strip().capitalize()} folder. I have displayed them on your screen."
        return True, f"[Action: Listed folder contents]\n{res}", preview_speech, False

    # 8b. Folder Organization Intent ("organize downloads", "arrange files in download folder", "sort files into folders")
    if any(w in t for w in ["organize", "arrange files", "sort files", "arrange them", "clean up downloads", "clean up folder"]) and any(f in t for f in ["download", "desktop", "document", "picture", "file", "folder", "them"]):
        target = "downloads"
        if "desktop" in t:
            target = "desktop"
        elif "document" in t:
            target = "documents"
        elif "picture" in t:
            target = "pictures"
        res = organize_folder(target)
        return True, f"[Action: {res}]", res, False

    # 8c. Create Folder Intent ("create folder work", "make a folder named projects")
    if any(p in t for p in ["create folder", "make a folder", "make folder", "create a folder"]):
        m = re.search(r'(?:create\s+(?:a\s+)?folder|make\s+(?:a\s+)?folder)(?:\s+named|\s+called)?\s+([a-zA-Z0-9_\-\\/\s]+)', t)
        if m:
            f_name = m.group(1).strip()
            res = create_folder(f_name)
            return True, f"[Action: {res}]", res, False

    # 9. Search Local Files ("search for file requirements.txt", "find file ...", "where is file ...")
    if any(t.startswith(prefix) for prefix in ["search for file ", "search file ", "find file ", "where is file ", "look for file ", "find the file "]):
        clean_q = re.sub(r'^(search for file|search file|find file|where is file|look for file|find the file)\s+', '', t).strip()
        clean_q = clean_q.strip('\'".,?! ')
        if clean_q:
            res = search_local_files(clean_q)
            speech = f"I searched for {clean_q} on your system. I have placed the matching files on your screen."
            return True, f"[Action: Searched for file '{clean_q}']\n{res}", speech, False

    # 10. Read File Content ("read file X", "show file X", "what is inside file X")
    if any(t.startswith(prefix) for prefix in ["read file ", "show file ", "view file ", "what is inside file ", "display file "]):
        file_target = re.sub(r'^(read file|show file|view file|what is inside file|display file)\s+', '', t).strip()
        file_target = file_target.strip('\'".,?! ')
        if file_target:
            res = read_file_content(file_target)
            speech = f"I have read {file_target} and placed its contents on your screen."
            return True, f"[Action: Read file '{file_target}']\n{res}", speech, False

    # 11. GitHub Intent
    if "github" in t and any(w in t for w in ["open", "launch", "show", "go to"]):
        res = open_url("https://github.com", browser=browser)
        return True, f"[Action: {res}]", "Opening GitHub for you.", False

    # 12. Screenshot Intents (open latest vs take new)
    if any(w in t for w in ["last screenshot", "latest screenshot", "recent screenshot", "previous screenshot"]):
        res = open_last_screenshot()
        return True, f"[Action: {res}]", res, False

    if "screenshot" in t and any(w in t for w in ["take", "capture", "grab", "save"]):
        res = take_screenshot()
        return True, f"[Action: {res}]", "Screenshot taken and saved to your Pictures folder.", False

    # 13. System Health & Resource Telemetry ("system condition", "cpu and gpu", "top processes")
    if any(p in t for p in [
        "system condition", "system status", "system health", "cpu and gpu", "cpu usage", "gpu usage",
        "memory usage", "ram usage", "resource usage", "processes taking", "systems are talking most",
        "talking most", "systems are taking most", "what is taking most memory", "top processes",
        "task manager", "system performance", "hardware telemetry", "how is my pc doing"
    ]):
        res = get_system_health()
        return True, f"[Action: System Telemetry Checked]\n{res}", res, False

    # 13b. Terminate / End Process Intent ("end chrome", "kill python", "close blender")
    if any(t.startswith(prefix) for prefix in ["end ", "kill ", "terminate "]):
        m = re.search(r'^(?:end|kill|terminate)\s+(?:process\s+|app\s+|application\s+)?([a-zA-Z0-9_.\s]+)', t)
        if m:
            proc_target = m.group(1).strip().strip("'\".,?! ")
            if proc_target not in ("all", "it", "this", "that"):
                res = close_app(proc_target)
                return True, f"[Action: {res}]", res, False

    # 13c. Folder Intent ("open work folder", "open downloads", "open pictures", "open minecraft tlauncher folder")
    if ("open" in t or "show" in t or "explore" in t) and any(w in t for w in ["folder", "downloads", "pictures", "desktop", "documents", "work", "workspace", "minecraft", "tlauncher"]):
        # Extract folder target cleanly between command verb and optional 'folder' suffix
        m = re.search(r'(?:open|show|explore)\s+(?:my\s+)?(?:the\s+)?(.+?)(?:\s+folder)?$', t)
        folder = m.group(1).strip() if m else ""
        folder = re.sub(r'^(my|the|a)\s+', '', folder).strip()
        folder = re.sub(r'\s+folder$', '', folder).strip()
        if not folder or folder in ("it", "that", "this"):
            folder = "work" if "work" in t else "downloads"
        res = open_folder(folder)
        p, display_name = resolve_folder_path(folder)
        return True, f"[Action: {res}]", f"Opening {display_name} folder for you.", False

    # 14. Terminal CLI Command Intent ("run command ipconfig", "run dir")
    if t.startswith("run command ") or t.startswith("execute command ") or t.startswith("run cli "):
        cmd = re.sub(r'^(run command|execute command|run cli)\s+', '', t).strip()
        if cmd:
            out = execute_command(cmd)
            lines = out.split("\n")
            preview = "\n".join(lines[:10]) + ("\n...(truncated)" if len(lines) > 10 else "")
            action_msg = f"[Action: Executed `{cmd}`]\n{preview}"
            return True, action_msg, f"Command {cmd} executed.", False

    # 15. Application Launch Intent (strictly check for app launch, ignore if tutorial/video/problem/search)
    if any(w in t for w in ["open", "launch", "start", "run"]) and not any(w in t for w in ["youtube", "video", "tutorial", "search", "problem", "explain", "how to", "lead code", "leetcode"]):
        if re.search(r'\b(vs\s*code|vscode|visual\s+studio\s+code)\b', t) or re.search(r'^(?:open|launch|start|run)\s+(?:the\s+)?code$', t):
            res = open_app("code")
            return True, f"[Action: {res}]", "Launching Visual Studio Code for you.", False
        for app in ["helium", "firefox", "chrome", "notepad", "terminal", "powershell", "cmd", "calculator", "calc", "explorer"]:
            if re.search(r'\b(?:open|launch|start|run)\s+(?:my\s+)?(?:the\s+)?' + app + r'\b', t) or re.search(r'\b' + app + r'\s+(?:app|application|browser)\b', t):
                res = open_app(app)
                app_disp = "Helium Browser" if app == "helium" else app.capitalize()
                return True, f"[Action: {res}]", f"Launching {app_disp} for you.", False

    return False, None, None, False

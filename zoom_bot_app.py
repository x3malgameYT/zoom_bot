import os
import sys
import re
import time
import random
import threading
import subprocess
import wave
import urllib.request
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

UPDATE_URL = "https://gist.githubusercontent.com/x3malgameYT/3c47d1b60c0711d57a1320cfb751d48d/raw/zoom_bot_app.py"
VERSION = "1.1.0"

names_list = []
stop_flag = False
audio_wav_path = None
drivers = []
drivers_lock = threading.Lock()
link_converted = False

DEFAULT_LINK = "https://us05web.zoom.us/wc/join/87231148657?pwd=eeGAnxxYrmEyPpQjBCOnGpa31TjGSH.1"

BG = "#0d0d0f"
BG2 = "#16161a"
ACCENT = "#00e676"
ACCENT2 = "#2979ff"
DANGER = "#ff1744"
WARN = "#ff9100"
TEXT = "#e0e0e0"
TEXT_DIM = "#7a7a85"
BORDER = "#25252c"


# ===== КОНВЕРТАЦИЯ ССЫЛКИ ZOOM =====

def convert_zoom_link(raw):
    """Превращает любую ссылку Zoom в формат веб-клиента /wc/join/."""
    raw = raw.strip()
    if not raw:
        return None, "Пустая ссылка"

    # Убираем кавычки и лишние символы
    raw = raw.strip('"').strip("'").strip()

    # Если уже wc/join — оставляем как есть
    if "/wc/join/" in raw:
        return raw, None

    # Меняем /j/ на /wc/join/
    if "/j/" in raw:
        converted = raw.replace("/j/", "/wc/join/")
        return converted, None

    # Ссылка без /j/ и /wc/ — пробуем найти ID конференции
    match = re.search(r"zoom\.us/(?:j|wc/join|s)/(\d+)", raw)
    if match:
        conf_id = match.group(1)
        # Извлекаем pwd если есть
        pwd_match = re.search(r"[?&]pwd=([^&]+)", raw)
        base = raw.split("/j/")[0] if "/j/" in raw else "https://us05web.zoom.us"
        # Определяем домен
        domain_match = re.search(r"(https?://[^/]+)", raw)
        domain = domain_match.group(1) if domain_match else "https://us05web.zoom.us"
        new_url = f"{domain}/wc/join/{conf_id}"
        if pwd_match:
            new_url += f"?pwd={pwd_match.group(1)}"
        return new_url, None

    return None, "Не удалось распознать ссылку Zoom"


def on_link_paste(event=None):
    """Автоконвертация при вставке."""
    root.after(50, auto_convert_link)


def auto_convert_link():
    """Читает ссылку из поля и конвертирует, если нужно."""
    global link_converted
    raw = link_text.get("1.0", tk.END).strip()
    if not raw:
        link_status.config(text="", fg=TEXT_DIM)
        return

    # Уже сконвертировано — не трогаем
    if "/wc/join/" in raw:
        link_status.config(text="✓ Формат веб-клиента", fg=ACCENT)
        link_converted = True
        return

    converted, err = convert_zoom_link(raw)
    if err:
        link_status.config(text=f"⚠ {err}", fg=WARN)
        link_converted = False
        return

    if converted and converted != raw:
        link_text.delete("1.0", tk.END)
        link_text.insert("1.0", converted)
        link_status.config(text="✓ Ссылка сконвертирована", fg=ACCENT)
        link_converted = True
        log(f"[LINK] Сконвертировано: {converted[:60]}...")
    else:
        link_status.config(text="✓ Формат OK", fg=ACCENT)
        link_converted = True


def manual_convert():
    """Кнопка ручной конвертации."""
    auto_convert_link()


# ===== ЗАГРУЗКА ФАЙЛОВ =====

def load_names():
    global names_list
    path = filedialog.askopenfilename(
        title="Выберите файл с именами",
        filetypes=[("Text files", "*.txt")]
    )
    if not path:
        return
    with open(path, "r", encoding="utf-8") as f:
        names_list = [line.strip() for line in f if line.strip()]
    if names_list:
        log(f"[+] Загружено имён: {len(names_list)}")
        status_names.config(text=f"Имена: {len(names_list)}", fg=ACCENT)
    else:
        log("[!] Файл пуст")


def check_wav_format(path):
    try:
        with wave.open(path, "rb") as w:
            channels = w.getnchannels()
            rate = w.getframerate()
            sampwidth = w.getsampwidth() * 8
            log(f"[i] WAV: {rate} Hz, {sampwidth} bit, каналов: {channels}")
            if rate != 48000 or sampwidth != 16 or channels != 2:
                log("[!] Формат не 48000/16/стерео — звук может не пойти")
                return False
            return True
    except Exception as e:
        log(f"[!] Не удалось прочитать WAV: {e}")
        return False


def load_audio():
    global audio_wav_path
    path = filedialog.askopenfilename(
        title="Выберите MP3 или WAV",
        filetypes=[("Audio", "*.mp3 *.wav *.ogg *.m4a"), ("All files", "*.*")]
    )
    if not path:
        return

    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    wav_path = os.path.join(base_dir, "bot_audio.wav")
    ext = os.path.splitext(path)[1].lower()

    if ext == ".wav":
        audio_wav_path = path
        log(f"[+] WAV загружен: {os.path.basename(path)}")
        check_wav_format(path)
        status_audio.config(text=f"Аудио: {os.path.basename(path)[:20]}", fg=ACCENT)
        return

    ffmpeg_cmd = "ffmpeg"
    local_ffmpeg = os.path.join(base_dir, "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        ffmpeg_cmd = local_ffmpeg

    try:
        subprocess.run(
            [ffmpeg_cmd, "-y", "-i", path, "-ar", "48000", "-ac", "2",
             "-c:a", "pcm_s16le", wav_path],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        audio_wav_path = wav_path
        log(f"[+] Сконвертировано в bot_audio.wav")
        check_wav_format(wav_path)
        status_audio.config(text="Аудио: bot_audio.wav", fg=ACCENT)
    except FileNotFoundError:
        log("[!] ffmpeg не найден")
    except Exception as e:
        log(f"[!] Ошибка конвертации: {e}")


def log(text):
    output_box.insert(tk.END, text + "\n")
    output_box.see(tk.END)


def find_chrome():
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def click_if_exists(driver, xpath, timeout=3):
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        el.click()
        return True
    except:
        return False


def refresh_bot_list():
    for widget in bot_list_frame.winfo_children():
        widget.destroy()
    with drivers_lock:
        snapshot = list(drivers)
    if not snapshot:
        tk.Label(bot_list_frame, text="Нет активных ботов", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=5)
        status_bots.config(text="Ботов: 0", fg=TEXT_DIM)
        return
    status_bots.config(text=f"Ботов: {len(snapshot)}", fg=ACCENT)
    for entry in snapshot:
        row = tk.Frame(bot_list_frame, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=f"  #{entry['id']}  {entry['name']}", bg=BG2, fg=TEXT,
                 font=("Segoe UI", 10), width=28, anchor="w").pack(side="left", padx=5, pady=4)
        tk.Button(row, text="MIC ON", command=lambda e=entry: mic_on_one(e),
                  bg="#0a5", fg="white", font=("Segoe UI", 9, "bold"),
                  width=10, bd=0, relief="flat").pack(side="left", padx=2)
        tk.Button(row, text="MIC OFF", command=lambda e=entry: mic_off_one(e),
                  bg=WARN, fg="white", font=("Segoe UI", 9, "bold"),
                  width=10, bd=0, relief="flat").pack(side="left", padx=2)
        tk.Button(row, text="MUSIC ▶", command=lambda e=entry: music_restart_one(e),
                  bg=ACCENT2, fg="white", font=("Segoe UI", 9, "bold"),
                  width=10, bd=0, relief="flat").pack(side="left", padx=2)
        tk.Button(row, text="MUSIC ■", command=lambda e=entry: music_stop_one(e),
                  bg="#a05", fg="white", font=("Segoe UI", 9, "bold"),
                  width=10, bd=0, relief="flat").pack(side="left", padx=2)


def mic_on_one(entry):
    def worker():
        d = entry["driver"]
        bot_id = entry["id"]
        try:
            selectors = [
                "//button[contains(@aria-label,'microphone')]",
                "//button[contains(@aria-label,'Микрофон')]",
                "//button[contains(@class,'join-audio')]",
                "//button[contains(text(),'Присоединиться к аудио')]",
                "//button[contains(text(),'Join Audio')]",
            ]
            clicked = False
            for sel in selectors:
                try:
                    for b in d.find_elements(By.XPATH, sel):
                        if b.is_displayed() and b.is_enabled():
                            b.click()
                            clicked = True
                            break
                except:
                    pass
                if clicked:
                    break
            d.execute_script("""
                try {
                    if (window.__fakeAudioStream) {
                        window.__fakeAudioStream.getAudioTracks().forEach(t => t.enabled = true);
                    } else {
                        navigator.mediaDevices.getUserMedia({audio: true}).then(s => {
                            window.__fakeAudioStream = s;
                        });
                    }
                } catch(e) {}
            """)
            log(f"[бот {bot_id}] MIC ON" + (" (кнопка)" if clicked else " (JS)"))
        except Exception as e:
            log(f"[бот {bot_id}] MIC ON ошибка: {e}")
    threading.Thread(target=worker, daemon=True).start()


def mic_off_one(entry):
    def worker():
        d = entry["driver"]
        bot_id = entry["id"]
        try:
            selectors = [
                "//button[contains(@aria-label,'mute')]",
                "//button[contains(@aria-label,'Mute')]",
                "//button[contains(@aria-label,'Выключить микрофон')]",
            ]
            clicked = False
            for sel in selectors:
                try:
                    for b in d.find_elements(By.XPATH, sel):
                        if b.is_displayed() and b.is_enabled():
                            b.click()
                            clicked = True
                            break
                except:
                    pass
                if clicked:
                    break
            d.execute_script("""
                try {
                    if (window.__fakeAudioStream) {
                        window.__fakeAudioStream.getAudioTracks().forEach(t => t.enabled = false);
                    }
                } catch(e) {}
            """)
            log(f"[бот {bot_id}] MIC OFF" + (" (кнопка)" if clicked else " (JS)"))
        except Exception as e:
            log(f"[бот {bot_id}] MIC OFF ошибка: {e}")
    threading.Thread(target=worker, daemon=True).start()


def music_restart_one(entry):
    def worker():
        d = entry["driver"]
        bot_id = entry["id"]
        try:
            d.execute_script("""
                try {
                    if (window.__fakeAudioStream) {
                        window.__fakeAudioStream.getAudioTracks().forEach(t => t.stop());
                    }
                    navigator.mediaDevices.getUserMedia({audio: true}).then(s => {
                        window.__fakeAudioStream = s;
                        window.__fakeAudioStream.getAudioTracks().forEach(t => t.enabled = true);
                    });
                } catch(e) {}
            """)
            log(f"[бот {bot_id}] музыка перезапущена")
        except Exception as e:
            log(f"[бот {bot_id}] MUSIC ▶ ошибка: {e}")
    threading.Thread(target=worker, daemon=True).start()


def music_stop_one(entry):
    def worker():
        d = entry["driver"]
        bot_id = entry["id"]
        try:
            d.execute_script("""
                try {
                    if (window.__fakeAudioStream) {
                        window.__fakeAudioStream.getAudioTracks().forEach(t => t.stop());
                    }
                } catch(e) {}
            """)
            log(f"[бот {bot_id}] музыка остановлена")
        except Exception as e:
            log(f"[бот {bot_id}] MUSIC ■ ошибка: {e}")
    threading.Thread(target=worker, daemon=True).start()


def enable_mic_all():
    with drivers_lock:
        snapshot = list(drivers)
    if not snapshot:
        log("[!] Нет активных ботов")
        return
    log(f"[MIC ON] Включаю у {len(snapshot)} ботов...")
    for e in snapshot:
        mic_on_one(e)


def disable_mic_all():
    with drivers_lock:
        snapshot = list(drivers)
    if not snapshot:
        log("[!] Нет активных ботов")
        return
    log(f"[MIC OFF] Выключаю у {len(snapshot)} ботов...")
    for e in snapshot:
        mic_off_one(e)


def restart_music_all():
    with drivers_lock:
        snapshot = list(drivers)
    if not snapshot:
        log("[!] Нет активных ботов")
        return
    if not audio_wav_path:
        log("[!] Аудио не загружено")
        return
    log(f"[MUSIC] Перезапуск у {len(snapshot)} ботов...")
    for e in snapshot:
        music_restart_one(e)


def stop_music_all():
    with drivers_lock:
        snapshot = list(drivers)
    if not snapshot:
        log("[!] Нет активных ботов")
        return
    log(f"[MUSIC STOP] У {len(snapshot)} ботов...")
    for e in snapshot:
        music_stop_one(e)


def start_bot(bot_id, link, eco_mode, headless_mode, wav_path):
    global stop_flag
    if stop_flag:
        return

    name = random.choice(names_list)
    log(f"[Бот {bot_id}] Запуск: {name}")

    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    profile_dir = os.path.join(base_dir, "profiles", f"bot_{bot_id}_{random.randint(100000, 999999)}")
    os.makedirs(profile_dir, exist_ok=True)

    chrome_path = find_chrome()

    opts = Options()
    if chrome_path:
        opts.binary_location = chrome_path

    opts.add_argument("--use-fake-ui-for-media-stream")
    opts.add_argument("--use-fake-device-for-media-stream")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--mute-audio")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-session-crashed-bubble")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_argument(f"--profile-directory=Profile{bot_id}")
    opts.add_argument("--disable-audio-track-processing")
    opts.add_argument("--disable-features=AudioServiceOutOfProcess")
    opts.add_argument("--enable-exclusive-audio")
    opts.add_argument("--audio-buffer-size=16")

    if wav_path and os.path.exists(wav_path):
        opts.add_argument(f"--use-file-for-fake-audio-capture={wav_path}")

    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.media_stream_camera": 2,
        "profile.default_content_setting_values.images": 2,
        "profile.managed_default_content_settings.images": 2,
        "hardware_acceleration_mode": False,
        "protocol_handler.excluded_schemes": {
            "zoommtg": False, "zoomus": False, "tel": False,
            "callto": False, "mailto": False,
        },
    })

    if eco_mode:
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-software-rasterizer")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--disable-plugins")
        opts.add_argument("--disable-images")
        opts.add_argument("--blink-settings=imagesEnabled=false")
        opts.add_argument("--disable-background-networking")
        opts.add_argument("--disable-sync")
        opts.add_argument("--disable-translate")
        opts.add_argument("--disable-default-apps")
        opts.add_argument("--metrics-recording-only")
        opts.add_argument("--safebrowsing-disable-auto-update")
        opts.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
        opts.add_argument("--window-size=400,300")
        opts.add_argument("--js-flags=--max-old-space-size=128")

    if headless_mode:
        opts.add_argument("--headless=new")
        opts.add_argument("--window-size=400,300")

    try:
        driver = webdriver.Chrome(options=opts)
    except Exception as e:
        log(f"[Бот {bot_id}] Ошибка запуска Chrome: {e}")
        return

    entry = {"id": bot_id, "driver": driver, "name": name}
    with drivers_lock:
        drivers.append(entry)
    root.after(0, refresh_bot_list)

    try:
        driver.get(link)
        wait = WebDriverWait(driver, 30)
        click_if_exists(driver, "//a[contains(text(),'браузер') or contains(text(),'browser')]", timeout=5)
        click_if_exists(driver, "//button[contains(text(),'браузер') or contains(text(),'browser')]", timeout=3)

        name_input = wait.until(EC.presence_of_element_located((By.ID, "input-for-name")))
        name_input.clear()
        name_input.send_keys(name)

        click_if_exists(driver, "//button[contains(text(),'Войти') or contains(text(),'Join')]", timeout=5)
        click_if_exists(driver, "//button[contains(@aria-label,'camera') or contains(@aria-label,'Камера')]", timeout=3)
        click_if_exists(driver, "//button[contains(text(),'Присоединиться к аудио') or contains(text(),'Join Audio') or contains(text(),'Присоединиться')]", timeout=5)

        log(f"[Бот {bot_id}] Подключён как {name}")

        while not stop_flag:
            time.sleep(2)

    except Exception as e:
        log(f"[Бот {bot_id}] Ошибка: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass
        with drivers_lock:
            drivers[:] = [d for d in drivers if d["driver"] != driver]
        root.after(0, refresh_bot_list)


def start_all():
    global stop_flag
    stop_flag = False
    with drivers_lock:
        drivers.clear()
    refresh_bot_list()

    # Автоконвертация перед запуском
    auto_convert_link()
    link = link_text.get("1.0", tk.END).strip()

    if not link:
        messagebox.showerror("Ошибка", "Введите ссылку на урок")
        return
    if "/wc/join/" not in link:
        messagebox.showerror("Ошибка", "Ссылка не в формате веб-клиента.\nПроверьте поле ссылки.")
        return
    if not names_list:
        messagebox.showerror("Ошибка", "Загрузите файл с именами")
        return
    try:
        count = int(count_entry.get().strip())
    except ValueError:
        messagebox.showerror("Ошибка", "Количество ботов — это число")
        return
    if count < 1 or count > 100:
        messagebox.showerror("Ошибка", "Количество ботов: от 1 до 100")
        return

    eco = eco_var.get()
    headless = headless_var.get()

    log(f"\n=== Запуск {count} ботов ===")
    log(f"Аудио: {os.path.basename(audio_wav_path) if audio_wav_path else 'НЕ ЗАГРУЖЕНО'}\n")

    for i in range(count):
        if stop_flag:
            break
        t = threading.Thread(target=start_bot, args=(i + 1, link, eco, headless, audio_wav_path), daemon=True)
        t.start()
        time.sleep(random.uniform(4, 9))


def stop_all():
    global stop_flag
    stop_flag = True
    log("\n[!] Остановка...")
    status_bots.config(text="Ботов: остановка...", fg=WARN)


def do_update():
    if not UPDATE_URL:
        messagebox.showinfo("Обновление", "Ссылка на обновление не задана (UPDATE_URL пустой).")
        return
    try:
        log("[UPDATE] Скачиваю новую версию...")
        req = urllib.request.Request(UPDATE_URL, headers={"User-Agent": "ZoomBot"})
        with urllib.request.urlopen(req, timeout=20) as r:
            new_code = r.read().decode("utf-8")
        if "def start_bot" not in new_code:
            log("[UPDATE] Файл не похож на код программы, отмена")
            return
        current_file = os.path.abspath(sys.argv[0])
        if current_file.endswith(".exe"):
            save_path = os.path.join(os.path.dirname(current_file), "new_version.py")
        else:
            save_path = current_file
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(new_code)
        log(f"[UPDATE] Новая версия сохранена: {save_path}")
        messagebox.showinfo("Обновление", f"Скачано.\n{save_path}\n\nПерезапустите приложение.")
    except Exception as e:
        log(f"[UPDATE] Ошибка: {e}")
        messagebox.showerror("Обновление", f"Не удалось:\n{e}")


# ===== ИНТЕРФЕЙС =====

root = tk.Tk()
root.title(f"Zoom Bot v{VERSION}")
root.geometry("880x900")
root.configure(bg=BG)
root.minsize(820, 720)

top = tk.Frame(root, bg=BG2, height=60)
top.pack(fill="x")
top.pack_propagate(False)

tk.Label(top, text="⚡ ZOOM BOT", bg=BG2, fg=ACCENT,
         font=("Segoe UI", 18, "bold")).pack(side="left", padx=20)

tk.Label(top, text=f"v{VERSION}", bg=BG2, fg=TEXT_DIM,
         font=("Segoe UI", 10)).pack(side="left")

tk.Button(top, text="⟳ Обновить", command=do_update, bg=ACCENT2, fg="white",
          font=("Segoe UI", 10, "bold"), bd=0, relief="flat",
          padx=15, pady=8).pack(side="right", padx=15)

status_frame = tk.Frame(root, bg=BG)
status_frame.pack(fill="x", padx=20, pady=(15, 5))

status_names = tk.Label(status_frame, text="Имена: не загружены", bg=BG, fg=TEXT_DIM,
                        font=("Segoe UI", 10))
status_names.pack(side="left", padx=(0, 20))

status_audio = tk.Label(status_frame, text="Аудио: не загружено", bg=BG, fg=TEXT_DIM,
                        font=("Segoe UI", 10))
status_audio.pack(side="left", padx=(0, 20))

status_bots = tk.Label(status_frame, text="Ботов: 0", bg=BG, fg=TEXT_DIM,
                       font=("Segoe UI", 10))
status_bots.pack(side="left")

# Ссылка
tk.Label(root, text="Ссылка на урок (вставьте любую — конвертируется сама):", bg=BG, fg=TEXT,
         font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(10, 5))

link_row = tk.Frame(root, bg=BG)
link_row.pack(fill="x", padx=20)

link_text = tk.Text(link_row, height=2, font=("Segoe UI", 10), wrap="word",
                    bg=BG2, fg=TEXT, insertbackground=ACCENT, bd=0,
                    highlightthickness=1, highlightbackground=BORDER)
link_text.insert("1.0", DEFAULT_LINK)
link_text.pack(side="left", fill="x", expand=True)

tk.Button(link_row, text="Convert", command=manual_convert, bg=ACCENT2, fg="white",
          font=("Segoe UI", 9, "bold"), bd=0, relief="flat",
          padx=10).pack(side="left", padx=(8, 0))

# Привязка событий вставки и потери фокуса
link_text.bind("<Control-v>", on_link_paste)
link_text.bind("<Control-V>", on_link_paste)
link_text.bind("<ButtonRelease-3>", on_link_paste)
link_text.bind("<FocusOut>", on_link_paste)

link_status = tk.Label(root, text="", bg=BG, fg=TEXT_DIM, font=("Segoe UI", 9))
link_status.pack(anchor="w", padx=20, pady=(2, 0))

# Количество
row_count = tk.Frame(root, bg=BG)
row_count.pack(fill="x", padx=20, pady=(10, 5))
tk.Label(row_count, text="Количество ботов:", bg=BG, fg=TEXT,
         font=("Segoe UI", 10)).pack(side="left")
count_entry = tk.Entry(row_count, width=10, font=("Segoe UI", 10),
                       bg=BG2, fg=TEXT, insertbackground=ACCENT, bd=0,
                       highlightthickness=1, highlightbackground=BORDER)
count_entry.insert(0, "10")
count_entry.pack(side="left", padx=10)

eco_var = tk.BooleanVar(value=False)
headless_var = tk.BooleanVar(value=False)

tk.Checkbutton(row_count, text="Экономный", variable=eco_var, bg=BG, fg=TEXT,
               selectcolor=BG2, activebackground=BG, activeforeground=ACCENT,
               font=("Segoe UI", 10)).pack(side="left", padx=(20, 10))

tk.Checkbutton(row_count, text="Headless", variable=headless_var, bg=BG, fg=TEXT,
               selectcolor=BG2, activebackground=BG, activeforeground=ACCENT,
               font=("Segoe UI", 10)).pack(side="left")

btn_frame = tk.Frame(root, bg=BG)
btn_frame.pack(pady=15)

def mk_btn(parent, text, cmd, color, w=16):
    return tk.Button(parent, text=text, command=cmd, bg=color, fg="white",
                     font=("Segoe UI", 10, "bold"), bd=0, relief="flat",
                     width=w, height=2, cursor="hand2")

mk_btn(btn_frame, "📁 Загрузить имена", load_names, "#333").pack(side="left", padx=5)
mk_btn(btn_frame, "🎵 Загрузить аудио", load_audio, "#553").pack(side="left", padx=5)
mk_btn(btn_frame, "▶ Запустить", start_all, "#0a7").pack(side="left", padx=5)
mk_btn(btn_frame, "■ Остановить", stop_all, "#a00").pack(side="left", padx=5)

ctrl_frame = tk.Frame(root, bg=BG)
ctrl_frame.pack(pady=(0, 10))
mk_btn(ctrl_frame, "🎤 MIC ON всем", enable_mic_all, "#0a5", 20).pack(side="left", padx=5)
mk_btn(ctrl_frame, "🔇 MIC OFF всем", disable_mic_all, WARN, 20).pack(side="left", padx=5)

ctrl_frame2 = tk.Frame(root, bg=BG)
ctrl_frame2.pack(pady=(0, 15))
mk_btn(ctrl_frame2, "▶ Музыка заново всем", restart_music_all, ACCENT2, 20).pack(side="left", padx=5)
mk_btn(ctrl_frame2, "■ Стоп музыку всем", stop_music_all, "#a05", 20).pack(side="left", padx=5)

tk.Label(root, text="Отдельное управление:", bg=BG, fg=TEXT,
         font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20)

bot_list_frame = tk.Frame(root, bg=BG)
bot_list_frame.pack(fill="x", padx=20, pady=(5, 10))

output_box = scrolledtext.ScrolledText(root, bg="#0a0a0c", fg=ACCENT,
                                        font=("Consolas", 10), bd=0,
                                        highlightthickness=1,
                                        highlightbackground=BORDER)
output_box.pack(padx=20, pady=(0, 20), fill="both", expand=True)

refresh_bot_list()

log(f"=== Zoom Bot v{VERSION} ===")
log("Автоконвертация ссылки включена — вставляйте любую ссылку Zoom")
log("1. Загрузите имена (names.txt)")
log("2. Загрузите WAV 48000 Hz")
log("3. Укажите количество")
log("4. Нажмите 'Запустить'\n")

# Автоконвертация ссылки по умолчанию
root.after(200, auto_convert_link)

root.mainloop()

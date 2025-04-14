import tkinter as tk
from tkinter import messagebox, OptionMenu, Checkbutton, Scale, Text, ttk
import keyboard
import mss
import pytesseract
from PIL import Image
import pygame
from gtts import gTTS
import pyttsx3
from pydub import AudioSegment
import os
import threading
import time
import json
from googletrans import Translator, LANGUAGES

# Configure Tesseract path
if os.environ.get("TESSERACT_PATH"):
    pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_PATH"]
else:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\ScreenReader\bin\tesseract\tesseract.exe"

class ScreenReaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Reader")
        self.root.geometry("600x900")
        
        # Initialize audio and TTS
        pygame.mixer.init()
        self.tts_engine = pyttsx3.init()
        self.base_rate = self.tts_engine.getProperty('rate')
        self.translator = Translator()
        
        # State
        self.regions = {}
        self.max_regions = 10
        self.is_active = False
        self.is_binding = False
        self.bind_index = None
        self.start_pos = None
        self.selection_window = None
        self.is_reading = False
        self.volume = 100
        self.speed = 1.0
        self.auto_read = False
        self.last_text = None
        self.last_slot = None
        self.repeat_key = "ctrl+r"
        self.mute_key = "ctrl+m"
        
        # Voices and OCR languages
        self.voices = self.tts_engine.getProperty('voices')
        self.voice_options = [v.name for v in self.voices]
        self.default_voice = self.voices[0].id if self.voices else None
        self.ocr_langs = list(LANGUAGES.keys())
        self.gtts_accents = ["com", "co.uk", "com.au"]
        
        # Colors
        self.colors = [
            "red", "blue", "green", "purple", "orange",
            "cyan", "magenta", "yellow", "brown", "pink"
        ]
        
        # Text log
        self.text_log = []
        
        # GUI
        self.label = tk.Label(root, text="Screen Reader", font=("Arial", 14))
        self.label.pack(pady=10)
        
        # Status indicator
        self.status_dot = tk.Label(root, text="●", fg="red", font=("Arial", 12))
        self.status_dot.pack()
        
        # Controls frame
        self.controls_frame = tk.Frame(root)
        self.controls_frame.pack(pady=5)
        
        # Volume, speed, pitch sliders
        tk.Label(self.controls_frame, text="Volume:").grid(row=0, column=0, padx=5)
        self.volume_slider = Scale(self.controls_frame, from_=0, to=100, orient="horizontal", command=self.update_volume)
        self.volume_slider.set(100)
        self.volume_slider.grid(row=0, column=1, padx=5)
        
        tk.Label(self.controls_frame, text="Speed:").grid(row=1, column=0, padx=5)
        self.speed_slider = Scale(self.controls_frame, from_=50, to=200, orient="horizontal", resolution=10)
        self.speed_slider.set(100)
        self.speed_slider.grid(row=1, column=1, padx=5)
        
        tk.Label(self.controls_frame, text="Pitch:").grid(row=2, column=0, padx=5)
        self.pitch_slider = Scale(self.controls_frame, from_=50, to=150, orient="horizontal", resolution=10)
        self.pitch_slider.set(100)
        self.pitch_slider.grid(row=2, column=1, padx=5)
        
        # Auto-read and dark mode
        self.auto_read_var = tk.BooleanVar()
        self.auto_read_check = Checkbutton(self.controls_frame, text="Auto-Read on Change", variable=self.auto_read_var, command=self.update_auto_read)
        self.auto_read_check.grid(row=3, column=0, columnspan=2, pady=5)
        
        self.dark_mode_var = tk.BooleanVar()
        self.dark_mode_check = Checkbutton(self.controls_frame, text="Dark Mode", variable=self.dark_mode_var, command=self.toggle_dark_mode)
        self.dark_mode_check.grid(row=4, column=0, columnspan=2, pady=5)
        
        # Repeat and mute keys
        tk.Label(self.controls_frame, text="Repeat Key:").grid(row=5, column=0, padx=5)
        self.repeat_entry = tk.Entry(self.controls_frame, width=10)
        self.repeat_entry.insert(0, self.repeat_key)
        self.repeat_entry.grid(row=5, column=1, padx=5)
        tk.Button(self.controls_frame, text="Set", command=self.set_repeat_key).grid(row=5, column=2)
        
        tk.Label(self.controls_frame, text="Mute Key:").grid(row=6, column=0, padx=5)
        self.mute_entry = tk.Entry(self.controls_frame, width=10)
        self.mute_entry.insert(0, self.mute_key)
        self.mute_entry.grid(row=6, column=1, padx=5)
        tk.Button(self.controls_frame, text="Set", command=self.set_mute_key).grid(row=6, column=2)
        
        # Bindings frame
        self.bind_frame = tk.Frame(root)
        self.bind_frame.pack(pady=10)
        self.bind_labels = []
        self.bind_voices = []
        self.bind_accents = []
        self.bind_ocr_langs = []
        self.bind_translate = []
        self.bind_enabled = []
        
        for i in range(self.max_regions):
            frame = tk.Frame(self.bind_frame)
            frame.pack(anchor="w", pady=2)
            lbl = tk.Label(frame, text=f"Slot {i+1}: Unbound", font=("Arial", 10), bg=self.colors[i], width=20)
            lbl.pack(side="left")
            self.bind_labels.append(lbl)
            
            voice_var = tk.StringVar(value=self.voice_options[0] if self.voice_options else "Default")
            voice_menu = OptionMenu(frame, voice_var, *self.voice_options)
            voice_menu.pack(side="left", padx=2)
            self.bind_voices.append(voice_var)
            
            accent_var = tk.StringVar(value="com")
            accent_menu = OptionMenu(frame, accent_var, *self.gtts_accents)
            accent_menu.pack(side="left", padx=2)
            self.bind_accents.append(accent_var)
            
            ocr_var = tk.StringVar(value="eng")
            ocr_menu = OptionMenu(frame, ocr_var, *self.ocr_langs)
            ocr_menu.pack(side="left", padx=2)
            self.bind_ocr_langs.append(ocr_var)
            
            translate_var = tk.BooleanVar()
            Checkbutton(frame, text="Translate", variable=translate_var).pack(side="left", padx=2)
            self.bind_translate.append(translate_var)
            
            enabled_var = tk.BooleanVar(value=True)
            Checkbutton(frame, text="Enabled", variable=enabled_var).pack(side="left", padx=2)
            self.bind_enabled.append(enabled_var)
            
            tk.Button(frame, text="Custom Key", command=lambda x=i: self.custom_bind(x)).pack(side="left", padx=2)
            tk.Button(frame, text="Clear", command=lambda x=i: self.clear_slot(x)).pack(side="left", padx=2)
            
            text_lbl = tk.Label(frame, text="", font=("Arial", 8), wraplength=400)
            text_lbl.pack(anchor="w")
            self.bind_labels.append(text_lbl)
        
        # Buttons
        self.bind_button = tk.Button(root, text="Bind Slot", command=self.start_binding)
        self.bind_button.pack(pady=5)
        
        self.toggle_button = tk.Button(root, text="Activate", command=self.toggle_active)
        self.toggle_button.pack(pady=5)
        
        self.save_button = tk.Button(root, text="Save Texts", command=self.save_texts)
        self.save_button.pack(pady=5)
        
        self.help_button = tk.Button(root, text="Show Hotkeys", command=self.show_hotkeys)
        self.help_button.pack(pady=5)
        
        self.reset_button = tk.Button(root, text="Reset Regions", command=self.reset_regions)
        self.reset_button.pack(pady=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(root, orient="horizontal", length=200, mode="determinate")
        self.progress.pack(pady=5)
        
        # Text log
        self.log_frame = tk.Frame(root)
        self.log_frame.pack(pady=10, fill="both", expand=True)
        tk.Label(self.log_frame, text="Recent Texts:", font=("Arial", 10)).pack(anchor="w")
        self.log_text = Text(self.log_frame, height=5, width=60, font=("Arial", 8))
        self.log_text.pack(fill="both", expand=True)
        
        # Load saved regions
        self.load_regions()
        
        # Keyboard hooks
        self.keyboard_thread = threading.Thread(target=self.keyboard_listener, daemon=True)
        self.keyboard_thread.start()
        
    def update_volume(self, value):
        self.volume = int(value)
        pygame.mixer.music.set_volume(self.volume / 100)
        self.tts_engine.setProperty('volume', self.volume / 100)
        
    def update_auto_read(self):
        self.auto_read = self.auto_read_var.get()
        
    def toggle_dark_mode(self):
        bg = "black" if self.dark_mode_var.get() else "SystemButtonFace"
        fg = "white" if self.dark_mode_var.get() else "black"
        self.root.configure(bg=bg)
        for widget in [self.label, self.log_frame] + self.bind_labels[::2] + self.bind_labels[1::2]:
            widget.configure(bg=bg, fg=fg)
        self.log_text.configure(bg=bg, fg=fg)
        
    def set_repeat_key(self):
        self.repeat_key = self.repeat_entry.get().strip()
        
    def set_mute_key(self):
        self.mute_key = self.mute_entry.get().strip()
        
    def start_binding(self):
        if not self.is_active:
            messagebox.showwarning("Warning", "Please activate the tool first!")
            return
        self.is_binding = True
        self.bind_index = None
        messagebox.showinfo("Bind Slot", "Press a key combo or click 'Custom Key'.")
        
    def custom_bind(self, slot):
        if not self.is_active:
            messagebox.showwarning("Warning", "Please activate the tool first!")
            return
        self.is_binding = True
        self.bind_index = slot
        messagebox.showinfo("Custom Key", "Press a key combo.")
        threading.Thread(target=self.wait_for_custom_key, daemon=True).start()
        
    def wait_for_custom_key(self):
        key = keyboard.read_hotkey(suppress=True)
        if self.bind_index is not None and key:
            self.regions[self.bind_index]["bind_key"] = key
            self.regions[self.bind_index]["read_key"] = key.replace("ctrl", "alt")
            self.update_bind_label(self.bind_index)
            self.start_selection()
            
    def toggle_active(self):
        self.is_active = not self.is_active
        self.toggle_button.config(text="Deactivate" if self.is_active else "Activate")
        self.status_dot.config(fg="green" if self.is_active else "red")
        if not self.is_active:
            self.is_binding = False
            self.bind_index = None
            if self.selection_window:
                self.selection_window.destroy()
                self.selection_window = None
                
    def keyboard_listener(self):
        while True:
            if not self.is_active:
                time.sleep(0.1)
                continue
                
            if keyboard.is_pressed("space") and self.is_reading:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.pause()
                else:
                    pygame.mixer.music.unpause()
                while keyboard.is_pressed("space"):
                    time.sleep(0.01)
                    
            if keyboard.is_pressed(self.repeat_key) and self.last_text:
                threading.Thread(target=self.read_text, args=(self.last_slot, self.last_text), daemon=True).start()
                while keyboard.is_pressed(self.repeat_key):
                    time.sleep(0.01)
                    
            if keyboard.is_pressed(self.mute_key):
                self.volume = 0 if self.volume > 0 else self.volume_slider.get()
                self.update_volume(self.volume)
                while keyboard.is_pressed(self.mute_key):
                    time.sleep(0.01)
                    
            for i in range(10):
                bind_key = self.regions.get(i, {}).get("bind_key", f"ctrl+{i+1 if i < 9 else 0}")
                read_key = self.regions.get(i, {}).get("read_key", f"alt+{i+1 if i < 9 else 0}")
                
                if keyboard.is_pressed(bind_key) and self.is_binding:
                    self.bind_index = i
                    self.start_selection()
                    while keyboard.is_pressed(bind_key):
                        time.sleep(0.01)
                    break
                    
                if keyboard.is_pressed(read_key) and i in self.regions and self.bind_enabled[i].get():
                    threading.Thread(target=self.read_region, args=(i,), daemon=True).start()
                    while keyboard.is_pressed(read_key):
                        time.sleep(0.01)
                    break
            time.sleep(0.01)
            
    def start_selection(self):
        if not self.is_binding or self.bind_index is None:
            return
            
        self.selection_window = tk.Toplevel(self.root)
        self.selection_window.attributes("-alpha", 0.3)
        self.selection_window.attributes("-fullscreen", True)
        self.selection_window.attributes("-topmost", True)
        
        self.canvas = tk.Canvas(self.selection_window, highlightthickness=0, bg="black")
        self.canvas.pack(fill="both", expand=True)
        
        self.start_pos = None
        self.rect_id = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
    def on_press(self, event):
        self.start_pos = (event.x, event.y)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline=self.colors[self.bind_index], width=2
        )
        
    def on_drag(self, event):
        if self.start_pos:
            self.canvas.coords(
                self.rect_id, self.start_pos[0], self.start_pos[1], event.x, event.y
            )
            
    def on_release(self, event):
        if self.start_pos:
            x1, y1 = self.start_pos
            x2, y2 = event.x, event.y
            left =11 min(x1, x2)
            top = min(y1, y2)
            right = max(x1, x2)
            bottom = max(y1, y2)
            
            self.regions[self.bind_index] = {
                "left": left,
                "top": top,
                "width": right - left,
                "height": bottom - top,
                "bind_key": self.regions.get(self.bind_index, {}).get("bind_key", f"ctrl+{self.bind_index+1 if self.bind_index < 9 else 0}"),
                "read_key": self.regions.get(self.bind_index, {}).get("read_key", f"alt+{self.bind_index+1 if self.bind_index < 9 else 0}"),
                "text": "",
                "voice": self.bind_voices[self.bind_index].get(),
                "accent": self.bind_accents[self.bind_index].get(),
                "ocr_lang": self.bind_ocr_langs[self.bind_index].get(),
                "translate": self.bind_translate[self.bind_index].get()
            }
            self.update_bind_label(self.bind_index)
            self.capture_and_read(self.bind_index)
            
            # Play chime
            chime_path = os.path.join(os.path.dirname(__file__), "chime.wav")
            if os.path.exists(chime_path):
                pygame.mixer.Sound(chime_path).play()
            
            self.selection_window.destroy()
            self.selection_window = None
            self.is_binding = False
            self.bind_index = None
            self.start_pos = None
            self.save_regions()
            
    def update_bind_label(self, index):
        bind_key = self.regions.get(index, {}).get("bind_key", f"Ctrl+{index+1 if index < 9 else 0}")
        read_key = self.regions.get(index, {}).get("read_key", f"Alt+{index+1 if index < 9 else 0}")
        self.bind_labels[index*2].config(text=f"Slot {index+1}: {bind_key} / {read_key}")
        
    def highlight_region(self, index):
        region = self.regions[index]
        highlight = tk.Toplevel(self.root)
        highlight.attributes("-alpha", 0.5)
        highlight.attributes("-topmost", True)
        highlight.overrideredirect(True)
        highlight.geometry(f"{region['width']}x{region['height']}+{int(region['left'])}+{int(region['top'])}")
        
        canvas = tk.Canvas(highlight, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_rectangle(0, 0, region['width'], region['height'], outline=self.colors[index], width=3)
        
        self.root.after(1000, highlight.destroy)
        
    def update_log(self, slot, text):
        timestamp = time.strftime("%H:%M")
        entry = f"Slot {slot+1}: {text[:50]}{'...' if len(text) > 50 else ''} ({timestamp})"
        self.text_log.append(entry)
        if len(self.text_log) > 5:
            self.text_log.pop(0)
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "\n".join(self.text_log))
        
    def capture_and_read(self, index):
        if not self.bind_enabled[index].get():
            return
            
        region = self.regions[index]
        with mss.mss() as sct:
            monitor = {
                "left": int(region["left"]),
                "top": int(region["top"]),
                "width": int(region["width"]),
                "height": int(region["height"])
            }
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            
            text = pytesseract.image_to_string(img, lang=region["ocr_lang"]).strip()
            if not text:
                print(f"No text found in slot {index+1}")
                return
                
            if region["translate"]:
                try:
                    text = self.translator.translate(text, dest="en").text
                except:
                    print("Translation failed")
                    
            self.regions[index]["text"] = text
            self.bind_labels[index*2+1].config(text=text[:50] + ("..." if len(text) > 50 else ""))
            self.update_log(index, text)
            self.highlight_region(index)
            
            if not self.auto_read or region.get("prev_text", "") != text:
                self.read_text(index, text)
            region["prev_text"] = text
            
    def read_text(self, index, text):
        self.is_reading = True
        self.last_text = text
        self.last_slot = index
        
        voice_name = self.regions[index]["voice"]
        voice_id = next((v.id for v in self.voices if v.name == voice_name), self.default_voice)
        
        # Update progress bar
        self.progress["maximum"] = len(text)
        self.progress["value"] = 0
        step = len(text) // 10 or 1
        
        try:
            self.tts_engine.setProperty('voice', voice_id)
            self.tts_engine.setProperty('rate', int(self.base_rate * (self.speed_slider.get() / 100)))
            self.tts_engine.setProperty('volume', self.volume / 100)
            # Approximate pitch with rate adjustment
            self.tts_engine.say(text)
            for i in range(0, len(text), step):
                self.progress["value"] = i
                self.root.update()
                time.sleep(0.1)
            self.tts_engine.runAndWait()
        except:
            try:
                tts = gTTS(text, lang="en", tld=self.regions[index]["accent"])
                audio_file = f"temp_{index}.mp3"
                tts.save(audio_file)
                audio = AudioSegment.from_mp3(audio_file)
                audio = audio.speedup(playback_speed=self.speed_slider.get() / 100)
                audio.export(audio_file, format="mp3")
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.set_volume(self.volume / 100)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    self.progress["value"] += step
                    self.root.update()
                    time.sleep(0.1)
                os.remove(audio_file)
            except Exception as e:
                print(f"gTTS error: {e}")
                
        self.progress["value"] = 0
        self.is_reading = False
        
    def read_region(self, index):
        if index in self.regions:
            self.capture_and_read(index)
            
    def save_texts(self):
        with open("screen_texts.txt", "w") as f:
            for i in range(self.max_regions):
                text = self.regions.get(i, {}).get("text", "")
                if text:
                    f.write(f"Slot {i+1}:\n{text}\n\n")
        messagebox.showinfo("Success", "Texts saved to screen_texts.txt")
        
    def show_hotkeys(self):
        hotkeys = []
        for i in range(self.max_regions):
            bind_key = self.regions.get(i, {}).get("bind_key", f"Ctrl+{i+1 if i < 9 else 0}")
            read_key = self.regions.get(i, {}).get("read_key", f"Alt+{i+1 if i < 9 else 0}")
            hotkeys.append(f"Slot {i+1}: Bind={bind_key}, Read={read_key}")
        hotkeys.append(f"Repeat Last: {self.repeat_key}")
        hotkeys.append(f"Mute: {self.mute_key}")
        messagebox.showinfo("Hotkeys", "\n".join(hotkeys))
        
    def clear_slot(self, slot):
        if slot in self.regions:
            del self.regions[slot]
            self.bind_labels[slot*2].config(text=f"Slot {slot+1}: Unbound", bg=self.colors[slot])
            self.bind_labels[slot*2+1].config(text="")
            self.save_regions()
            
    def reset_regions(self):
        self.regions.clear()
        for i in range(self.max_regions):
            self.bind_labels[i*2].config(text=f"Slot {i+1}: Unbound", bg=self.colors[i])
            self.bind_labels[i*2+1].config(text="")
        self.save_regions()
        
    def save_regions(self):
        with open("regions.json", "w") as f:
            json.dump(self.regions, f)
            
    def load_regions(self):
        if os.path.exists("regions.json"):
            with open("regions.json", "r") as f:
                self.regions = json.load(f)
                for i in self.regions:
                    i = int(i)
                    self.update_bind_label(i)
                    self.bind_voices[i].set(self.regions[i]["voice"])
                    self.bind_accents[i].set(self.regions[i]["accent"])
                    self.bind_ocr_langs[i].set(self.regions[i]["ocr_lang"])
                    self.bind_translate[i].set(self.regions[i]["translate"])
                    self.bind_labels[i*2+1].config(text=self.regions[i]["text"][:50] + ("..." if len(self.regions[i]["text"]) > 50 else ""))
                    
    def __del__(self):
        pygame.mixer.quit()
        self.tts_engine.stop()
        self.save_regions()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenReaderApp(root)
    root.mainloop()
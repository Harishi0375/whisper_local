import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile, os
from faster_whisper import WhisperModel

# --- Config ---
SAMPLE_RATE = 16000
LANGUAGES = {
    "English": "en",
    "German": "de",
    "Tamil": "ta",
}

class WhisperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Whisper Transcriber")
        self.root.geometry("600x500")
        self.recording = False
        self.audio_data = []
        self.model = None

        self._build_ui()
        self._load_model("small")

    def _build_ui(self):
        top = tk.Frame(self.root, pady=8)
        top.pack(fill="x", padx=12)

        tk.Label(top, text="Model:").pack(side="left")
        self.model_var = tk.StringVar(value="small")
        model_menu = ttk.Combobox(top, textvariable=self.model_var, width=8,
            values=["tiny", "base", "small", "medium", "large"], state="readonly")
        model_menu.pack(side="left", padx=(4, 16))
        model_menu.bind("<<ComboboxSelected>>", lambda e: self._load_model(self.model_var.get()))

        tk.Label(top, text="Language:").pack(side="left")
        self.lang_var = tk.StringVar(value="English")
        lang_menu = ttk.Combobox(top, textvariable=self.lang_var, width=14,
            values=list(LANGUAGES.keys()), state="readonly")
        lang_menu.pack(side="left", padx=4)

        self.rec_btn = tk.Button(self.root, text="🎙 Start Recording",
            font=("", 13, "bold"), bg="#e74c3c", fg="white",
            relief="raised", padx=20, pady=10,
            command=self._toggle_recording)
        self.rec_btn.pack(pady=10)

        self.status_var = tk.StringVar(value="Loading model...")
        tk.Label(self.root, textvariable=self.status_var, fg="gray").pack()

        tk.Label(self.root, text="Transcription:", anchor="w").pack(fill="x", padx=12)
        self.text_box = scrolledtext.ScrolledText(self.root, wrap="word",
            font=("", 11), height=12)
        self.text_box.pack(fill="both", expand=True, padx=12, pady=(4, 6))
        self.text_box.bind("<Control-a>", self._select_all)

        tk.Button(self.root, text="📋 Copy to Clipboard",
            command=self._copy).pack(pady=(0, 10))

    def _load_model(self, size):
        self.status_var.set(f"Loading {size} model...")
        self.rec_btn.config(state="disabled")
        def load():
            self.model = WhisperModel(size, device="cpu", compute_type="int8")
            self.status_var.set(f"Ready ({size} model)")
            self.rec_btn.config(state="normal")
        threading.Thread(target=load, daemon=True).start()

    def _select_all(self, event):
        self.text_box.tag_add("sel", "1.0", "end")
        return "break"

    def _toggle_recording(self):
        if not self.recording:
            if not self.model:
                return
            self.recording = True
            self.audio_data = []
            self.rec_btn.config(bg="#c0392b", text="⏹ Stop & Transcribe")
            self.status_var.set("Recording...")

            def record():
                with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                    dtype="float32") as stream:
                    while self.recording:
                        chunk, _ = stream.read(1024)
                        self.audio_data.append(chunk)
            threading.Thread(target=record, daemon=True).start()
        else:
            self.recording = False
            self.rec_btn.config(bg="#e74c3c", text="🎙 Start Recording")
            self.status_var.set("Transcribing...")

            def transcribe():
                if not self.audio_data:
                    self.status_var.set("No audio captured.")
                    return
                audio = np.concatenate(self.audio_data, axis=0).flatten()
                audio_int16 = (audio * 32767).astype(np.int16)

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_path = f.name
                wav.write(tmp_path, SAMPLE_RATE, audio_int16)

                lang_code = LANGUAGES[self.lang_var.get()]
                segments, info = self.model.transcribe(tmp_path, language=lang_code)
                text = " ".join(s.text for s in segments).strip()
                os.unlink(tmp_path)

                self.text_box.delete("1.0", "end")
                self.text_box.insert("end", text)
                self.status_var.set(f"Done — detected: {info.language}")

            threading.Thread(target=transcribe, daemon=True).start()

    def _copy(self):
        text = self.text_box.get("1.0", "end").strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Copied to clipboard!")

if __name__ == "__main__":
    root = tk.Tk()
    WhisperApp(root)
    root.mainloop()
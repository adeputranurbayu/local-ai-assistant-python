import os
import wave
import threading
import subprocess
import json
import re
import time
import pyaudio
import threading
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showinfo
from pydub import AudioSegment
from pydub.playback import play, _play_with_simpleaudio
from RealtimeTTS import TextToAudioStream, OrpheusEngine
from faster_whisper import WhisperModel
from openai import OpenAI
from PIL import Image, ImageTk

# ======================= CONFIG =========================
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 550
TTS_TEMP_FILE = "bot_voice.wav"
STT_TEMP_FILE = "user_voice.wav"
ASSISTANT_ROLE = """
You are a helpfull assistant.
"""

def run_rhubarb(wav_path=TTS_TEMP_FILE, json_path="mouth.json"):
    rhubarb_path = os.path.join("bin", "rhubarb.exe")
    cmd = [rhubarb_path, "-f", "json", "-o", json_path, wav_path]
    subprocess.run(cmd, check=True)
    with open(json_path, "r") as f:
        return json.load(f)

# ======================= MODELS =========================
stt_model = "Systran/faster-distil-whisper-large-v2"
stt_engine = WhisperModel(stt_model, device="cuda", compute_type="float16")
llm_model = "deepseek-r1-distill-qwen-1.5b"
llm_engine = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
tts_model = "orpheus-3b-0.1-ft"
tts_engine = OrpheusEngine(model=tts_model)
tts_engine.set_voice("dan")

# ======================= STATES =========================
is_generating = False
is_speaking = False
finish_generating = True
history = []
phoneme_to_sprite = {
    "A": "A.png",
    "B": "B.png",
    "C": "C.png",
    "D": "D.png",
    "E": "B.png",
    "F": "C.png",
    "G": "A.png",
    "H": "B.png",
    "X": "A.png",
    "rest": "A.png"
}

# ======================= UTILS ==========================
def cleanup_temp_files():
    for f in [TTS_TEMP_FILE, STT_TEMP_FILE, "rhubarb_input.wav", "mouth.json"]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception as e:
            print(f"Error deleting {f}: {e}")

# ======================= AUDIO ==========================
class VoiceRecorder:
    def __init__(self, filename=STT_TEMP_FILE):
        self.filename = filename
        self.recording = False
        self.thread = None

    def start(self):
        self.recording = True
        self.thread = threading.Thread(target=self._record)
        self.thread.start()

    def stop(self):
        self.recording = False
        if self.thread:
            self.thread.join()
            self.thread = None

    def _record(self):
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        CHUNK = 1024

        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS,
                            rate=RATE, input=True,
                            frames_per_buffer=CHUNK)

        frames = []
        while self.recording:
            data = stream.read(CHUNK)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        audio.terminate()

        with wave.open(self.filename, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))

def convert_wav_for_rhubarb(infile, outfile):
    audio = AudioSegment.from_file(infile)
    audio = audio.set_channels(1).set_frame_rate(44100).set_sample_width(2)
    audio.export(outfile, format="wav")

# ======================= CHAT LOGIC =====================
def stt_uservoice():
    global finish_generating
    if finish_generating == False:
        please_wait ()
        return
    finish_generating = False
    loading_button()
    
    segments, _ = stt_engine.transcribe(STT_TEMP_FILE)
    stt_result = " ".join([s.text for s in segments])

    if not stt_result.strip():
        showinfo(title="Error", message="Please speak correctly")
        finish_generating = True
        return
    
    add_message(stt_result, sender="user")
    generate_response(stt_result)
    print("you make with voice")

def checktext():
    global TEXT_INPUT, finish_generating
    if finish_generating == False:
        return
    finish_generating = False
    loading_button()

    sentences = TEXT_INPUT.get().strip()
    if not sentences:
        showinfo(title="Error", message="Please type correctly")
        finish_generating = True
        return
    
    add_message(sentences, sender="user")
    generate_response(sentences)

def add_message(text, sender="user"):
    wrapper = tk.Frame(scrollable_frame, bg="white")
    wrapper.pack(fill="x", padx=10, pady=4)

    bubble_color = "#DCF8C6" if sender == "user" else "#E6E6E6"
    sticky = "e" if sender == "user" else "w"
    col = 1 if sender == "user" else 0

    wrapper.grid_columnconfigure(0, weight=1)
    wrapper.grid_columnconfigure(1, weight=1)

    bubble = tk.Label(
        wrapper,
        text=text,
        bg=bubble_color,
        fg="black",
        justify="left",
        wraplength=300,
        padx=10,
        pady=5,
        bd=1,
        relief="solid"
    )
    bubble.grid(row=0, column=col, sticky=sticky, padx=10)
    canvas.update_idletasks()
    canvas.yview_moveto(1.0)

def generate_response(user_input):
    global is_generating, history
    if is_generating:
        return

    is_generating = True
    try:
        if not history:
            history.append({"role": "system", "content": ASSISTANT_ROLE})
        history.append({"role": "user", "content": user_input})

        response = llm_engine.chat.completions.create(
            model=llm_model,
            messages=history,
            stream=False
        )
        answer = re.sub(r"(?:.*?</think>)", "", response.choices[0].message.content, flags=re.DOTALL).strip()
        history.append({"role": "assistant", "content": answer})

        add_message(answer, sender="system")
        print(history)
        threading.Thread(target=generate_voice, args=(answer,), daemon=True).start()
    finally:
        is_generating = False

#Generate voice and animation
def animate_lipsync(mouth_data, start_time, index=0):
    if index >= len(mouth_data["mouthCues"]):
        return_to_idle_sprite()
        return

    phoneme = mouth_data["mouthCues"][index]
    t0 = phoneme["start"]
    value = phoneme.get("value", "A")
    sprite = phoneme_to_sprite.get(value, "A.png")
    now = time.time() - start_time

    if now >= t0:
        photo = sprite_cache.get(value, sprite_cache["A"])
        sprite_label.config(image=photo)
        sprite_label.image = photo
        window.after(1, lambda: animate_lipsync(mouth_data, start_time, index + 1))
    else:
        window.after(5, lambda: animate_lipsync(mouth_data, start_time, index))

def generate_voice(llm_answer):
    global is_speaking, finish_generating
    if is_speaking:
        return

    is_speaking = True
    try:
        stream = TextToAudioStream(tts_engine, muted=True)
        cleaned_text = llm_answer.strip().replace("\x00", "").replace("\n", " ")
        if not cleaned_text:
            raise ValueError("Empty or invalid response from LLM")

        stream.feed(cleaned_text)
        stream.play(output_wavfile=TTS_TEMP_FILE)

        rhubarb_input = "rhubarb_input.wav"
        convert_wav_for_rhubarb(TTS_TEMP_FILE, rhubarb_input)
        mouth_data = run_rhubarb(rhubarb_input)

        tts_audio = AudioSegment.from_wav(TTS_TEMP_FILE)

        # Play + Animate in sync
        play_obj = _play_with_simpleaudio(tts_audio)
        start_time = time.time()

        window.after(0, lambda: animate_lipsync(mouth_data, start_time))

        play_obj.wait_done()
        return_to_idle_sprite()
        window.after(100, lambda: showinfo(title="Report", message=llm_answer))
    except Exception as e:
        window.after(100, lambda: showinfo(title="Error", message=f"Failed to generate voice: {e}"))
    finally:
        for f in [TTS_TEMP_FILE, "rhubarb_input.wav", "mouth.json"]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                print(f"Error deleting {f}: {e}")
        is_speaking = False
        finish_generating = True
        loading_button()

# ======================= GUI SETUP ======================
window = tk.Tk()
window.configure(bg="white")
window.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
window.resizable(False, False)
window.title("Visual Assistant")

style = ttk.Style()
style.configure("TEntry", fieldbackground="white", background="white")
style.configure("TLabel", background="white")
style.configure("TFrame", background="white")

# =================== MAIN FRAME (GRID PARENT) ===================
main_frame = ttk.Frame(window)
main_frame.pack(fill="both", expand=True)

main_frame.columnconfigure(0, weight=1)
main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(0, weight=1)
main_frame.rowconfigure(1, weight=0)

# =================== CHAT AREA (LEFT) ===================
chat_frame = ttk.Frame(main_frame)
chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 5))

canvas = tk.Canvas(chat_frame, bg="white", highlightthickness=0)
scrollbar = ttk.Scrollbar(chat_frame, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas, bg="white")

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)
canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)
canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# =================== SPRITE (RIGHT SIDE) ===================
def return_to_idle_sprite():
    sprite_label.config(image=sprite_cache["A"])
    sprite_label.image = sprite_cache["A"]
    
sprite_label = tk.Label(main_frame, bg="white")
sprite_label.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(0, 10), pady=10)

sprite_cache = {}
for key, filename in phoneme_to_sprite.items():
    path = os.path.join("sprites", filename)
    img = Image.open(path).resize((512, 512))
    sprite_cache[key] = ImageTk.PhotoImage(img)

return_to_idle_sprite()

# =================== CONTROL BUTTONS (BOTTOM LEFT) ===================
input_frame = ttk.Frame(main_frame)
input_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

recorder = VoiceRecorder()
voicemenu = textmenu = button_textchat = button_voicechat = button_cancel = TEXT_INPUT = None
button_generateby_voice = button_generateby_text = None

def voicechat():
    global button_voicechat
    recorder.start()
    button_voicechat.config(text="Stop record 🟥", command=stop_record)

def stop_record():
    recorder.stop()
    finish_record()

def finish_record():
    global voicemenu, button_textchat, button_voicechat, button_cancel, button_generateby_voice
    for item in [button_voicechat, button_textchat]:
        item.destroy()
    button_voicechat = button_textchat = None

    button_play = ttk.Button(input_frame, text="Play ▶️", command=play_uservoice)
    button_play.pack(padx=10, pady=5, fill="x", expand=True)

    button_generateby_voice = ttk.Button(input_frame, text="Generate ✅", command=stt_uservoice)
    button_generateby_voice.pack(padx=10, pady=5, fill="x", expand=True)

    button_cancel = ttk.Button(input_frame, text="Back", command=return_idle)
    button_cancel.pack(padx=10, pady=10, fill="x", expand=True)

    voicemenu = [button_play, button_generateby_voice]

    loading_button()

def play_uservoice():
    audio = AudioSegment.from_wav(STT_TEMP_FILE)
    play(audio)

def textchat():
    global TEXT_INPUT, textmenu, button_textchat, button_voicechat, button_cancel, button_generateby_text
    for item in [button_voicechat, button_textchat]:
        item.destroy()
    button_voicechat = button_textchat = None

    label_textinput = ttk.Label(input_frame, text="Your Chat:")
    label_textinput.pack(padx=10, pady=3, fill="x", expand=True)

    TEXT_INPUT = tk.StringVar()
    entry_textinput = ttk.Entry(input_frame, textvariable=TEXT_INPUT)
    entry_textinput.pack(padx=10, pady=10, fill="x", expand=True)

    button_generateby_text = ttk.Button(input_frame, text="Generate ✅", command=checktext)
    button_generateby_text.pack(padx=10, pady=3, fill="x", expand=True)

    button_cancel = ttk.Button(input_frame, text="Back", command=return_idle)
    button_cancel.pack(padx=10, pady=10, fill="x", expand=True)

    textmenu = [label_textinput, entry_textinput, button_generateby_text]

    loading_button()
    
def return_idle():
    global voicemenu, textmenu, button_textchat, button_voicechat, button_cancel
    for item in [voicemenu, textmenu]:
        if item:
            for btn in item:
                btn.destroy()
    voicemenu = textmenu = None
    if button_cancel != None:
        button_cancel.destroy()
    button_cancel = None

    button_voicechat = ttk.Button(input_frame, text="Speak 🔴", command=voicechat)
    button_voicechat.pack(padx=10, pady=10, fill="x", expand=True)

    button_textchat = ttk.Button(input_frame, text="Text Chat", command=textchat)
    button_textchat.pack(padx=10, pady=10, fill="x", expand=True)

def loading_button():
    global finish_generating, button_generateby_text, button_generateby_voice
    try:
        if button_generateby_voice and button_generateby_voice.winfo_exists():
            if not finish_generating:
                button_generateby_voice.config(text="Loading, Please Wait", command=please_wait)
            else:
                button_generateby_voice.config(text="Generate ✅", command=stt_uservoice)

        if button_generateby_text and button_generateby_text.winfo_exists():
            if not finish_generating:
                button_generateby_text.config(text="Loading, Please Wait", command=please_wait)
            else:
                button_generateby_text.config(text="Generate ✅", command=checktext)

    except Exception as e:
        print("loading_button error:", e)

def please_wait():
    if finish_generating == False:
        showinfo(title="Error", message="Please wait, your command is on progress")

return_idle()

# ======================= EXIT HOOK ======================
def on_exit():
    try:
        subprocess.run(["lms", "unload", "--all"])
        subprocess.run(["lms", "server", "stop"])
    except Exception as e:
        print("Unload error:", e)
    cleanup_temp_files()
    window.destroy()

window.protocol("WM_DELETE_WINDOW", on_exit)
window.mainloop()
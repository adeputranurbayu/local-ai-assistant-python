# Local AI Assistant Python (LAIAP)

A multimodal Python-based AI Assistant that runs **100% offline**. This project integrates speech recognition (English), local large language models, and voice output results with a visual sprite interface.

## Tech Stack & Models
This project utilizes a local pipeline to ensure privacy and performance:

- **Speech-to-Text (STT):** `faster-whisper` 
- **Large Language Model (LLM):** `DeepSeek-R1-Distill-Qwen-1.5B` via **LM Studio** local server.
- **Text-to-Speech (TTS):** `RealtimeTTS` with `Orpheus-3B` engine.
- **Lipsync:** `Rhubarb Lip Sync` for automatic sprite animation.
- **Interface:** `Tkinter` for the main UI and sprite rendering.

## System Requirements
- **OS:** Windows/Linux/MacOS
- **Hardware:** Recommended 8GB+ VRAM (RTX Series) for smooth local inference.
- **Software:** [LM Studio](https://lmstudio.ai/) running a local inference server on port 1234.

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/adeputranurbayu/local-ai-assistant-python
   cd local-ai-assistant-python
   ```
2. **Install Dependencies:**
   ```bash
   python -m venv venv
   call venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Download Model:**
   - Download Rhubarb Lip Sync v1.14 (Windows/Mac/Linux) from [here](https://github.com/DanielSWolf/rhubarb-lip-sync/releases) 
    . Create a folder named "bin" in the root directory and place rhubarb.exe inside it.
   
   - Install [LM Studio](https://lmstudio.ai/) then download deepseek-r1-distill-qwen-1.5b and orpheus-3b-0.1-ft from LM Studio

4. **Run the Application:**
   Double-Click the run.bat file


Built by Ade PNB

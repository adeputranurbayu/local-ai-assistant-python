call venv\Scripts\activate.bat
lms server start
lms load orpheus-3b-0.1-ft
lms load deepseek-r1-distill-qwen-1.5b
python main.py
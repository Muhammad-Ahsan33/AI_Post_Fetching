from groq import Groq
import time
import os
import dotenv
# --- Load environment variables ---
dotenv.load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# --- Load classification prompt ---
PROMPT_FILE = os.path.join(BASE_DIR, "commission_filter.txt")
if os.path.exists(PROMPT_FILE):
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
    print("[AI] Loaded SYSTEM_PROMPT from file.")
else:
    print("[AI] Prompt file not found, using fallback prompt.")


client = Groq(api_key="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")

while True:
    try:
        response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that helps people learn programming."},
                    {"role": "user", "content": "Give an essay on the importance of learning programming. max 10000 words"},
                ],
                temperature=0.0,
                max_tokens=5000,
                top_p=1.0,
            )
        print(response.choices[0].message.content)  
    except Exception as e:
        print("Hit limit or error:", e)
        break

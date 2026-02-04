# import json
# import os
# import hashlib
# from typing import Optional, Dict
# from groq import Groq
# # from .config import get_env
# import os
# import dotenv

# # Load environment variables
# dotenv.load_dotenv()

# # Load Groq API Key
# GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# client = Groq(api_key=GROQ_API_KEY)

# # Load classification prompt
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# PROMPT_FILE = os.path.join(BASE_DIR, "commission_filter.txt")

# with open(PROMPT_FILE, "r", encoding="utf-8") as f:
#     SYSTEM_PROMPT = f.read()

# if( os.path.exists(PROMPT_FILE)):
#     print("[AI] Loaded SYSTEM_PROMPT from file.")
# else:
#     print("[AI] File not found → should use fallback, but currently crashes before")

# # Confidence thresholds
# CONFIDENCE_HIGH = 0.80
# CONFIDENCE_MEDIUM = 0.50
# CONFIDENCE_LOW = 0.20

# # Buyer keywords for pre-filtering (Stage 1)
# BUYER_KEYWORDS = [
#     "looking for artist",
#     "looking to commission",
#     "looking to comm",
#     "need artist",
#     "need to commission",
#     "want to commission",
#     "wanna commission",
#     "hiring artist",
#     "seeking artist",
#     "seeking animator",
#     "someone to commission",
#     "someone to comm",
#     "anyone know an artist",
#     "need to find artist",
#     "trying to find artist",
#     "might commission",
#     "going to commission",
#     "willing to commission",
#     "can someone draw",
#     "need drawn",
#     "want drawn",
# ]

# # Seller keywords → HARD REJECT
# SELLER_KEYWORDS = [
#     "commissions open",
#     "comms open",
#     "work slots open",
#     "slots open",
#     "available services",
#     "taking commissions",
#     "my commissions",
#     "my comms",
#     "my rates",
#     "price sheet",
#     "commission sheet",
#     "portfolio",
#     "check my portfolio",
#     "vgen",
#     "ko-fi",
#     "gumroad",
#     "finished commission",
#     "completed commission",
#     "i did for",
#     "i made for",
# ]

# # Buyer verb gate (MANDATORY)
# BUYER_VERBS = [
#     "need",
#     "looking",
#     "want",
#     "seeking",
#     "hiring"
# ]


# def generate_content_hash(text: str) -> str:
#     return hashlib.sha256(text.encode("utf-8")).hexdigest()


# def quick_keyword_filter(text: str) -> Optional[str]:
#     """
#     Stage 1: Fast keyword-based pre-filtering
#     Returns:
#       - "seller" → artist advertising (skip LLM)
#       - "buyer"  → likely buyer (send to LLM)
#       - None     → unclear
#     """
#     text_lower = text.lower()

#     # HARD seller rejection
#     if any(keyword in text_lower for keyword in SELLER_KEYWORDS):
#         return "seller"

#     # Buyer verb gate (must exist)
#     if not any(verb in text_lower for verb in BUYER_VERBS):
#         return None

#     # Buyer keyword match
#     if any(keyword in text_lower for keyword in BUYER_KEYWORDS):
#         return "buyer"

#     return None


# def detect_prompt_injection(text: str) -> bool:
#     injection_patterns = [
#         "ignore previous",
#         "new instructions",
#         "system:",
#         "assistant:",
#         "ignore all",
#         "forget everything",
#         "override",
#         "disregard",
#         "you are now",
#         "new role",
#         "act as",
#         "jailbreak",
#     ]

#     text_lower = text.lower()
#     matches = sum(1 for p in injection_patterns if p in text_lower)

#     if matches >= 2:
#         return True

#     high_risk = [
#         "ignore previous instructions",
#         "system: you are",
#         "forget your role",
#     ]

#     return any(p in text_lower for p in high_risk)


# def classify_post(text: str, use_two_stage: bool = True) -> Optional[Dict]:
#     if not text or not text.strip():
#         return None

#     content_hash = generate_content_hash(text)

#     if detect_prompt_injection(text):
#         return {
#             "is_commission": False,
#             "confidence": 0.0,
#             "reason": "Potential prompt injection detected",
#             "content_hash": content_hash,
#         }

#     # Stage 1: Keyword filtering
#     if use_two_stage:
#         result = quick_keyword_filter(text)

#         if result == "seller":
#             return {
#                 "is_commission": False,
#                 "confidence": 0.85,
#                 "reason": "Artist advertising or self-promotion detected",
#                 "content_hash": content_hash,
#             }

#     # Stage 2: LLM classification
#     try:
#         messages = [
#             {"role": "system", "content": SYSTEM_PROMPT},
#             {"role": "user", "content": text},
#         ]

#         response = client.chat.completions.create(
#             model="llama-3.1-8b-instant",
#             messages=messages,
#             temperature=0.0,
#             max_tokens=150,
#             top_p=1.0,
#         )

#         raw_output = response.choices[0].message.content.strip()

#         if raw_output.startswith("```"):
#             raw_output = "\n".join(
#                 line for line in raw_output.split("\n") if not line.startswith("```")
#             )
#             if raw_output.startswith("json"):
#                 raw_output = raw_output[4:].strip()
        
#         result = json.loads(raw_output)


#         if not isinstance(result.get("is_commission"), bool):
#             return None

#         confidence = result.get("confidence", 0.5)
#         if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
#             confidence = 0.5

#         result["confidence"] = float(confidence)
#         result["reason"] = result.get("reason", "No reason provided")
#         result["content_hash"] = content_hash

#         # FINAL seller self-promotion safety net
#         if result["is_commission"]:
#             seller_self_refs = [
#                 "my commissions",
#                 "my comms",
#                 "my work",
#                 "my art",
#                 "i offer",
#                 "dm me",
#             ]
#             if any(p in text.lower() for p in seller_self_refs):
#                 result["is_commission"] = False
#                 result["confidence"] = 0.1
#                 result["reason"] = "Author is promoting their own services"

#         return result

#     except Exception as e:
#         print(f"[AI] ❌ Classification failed: {e}")
#         return None


# def classify_batch(posts: list[str], max_workers: int = 3) -> list[Optional[Dict]]:
#     return [classify_post(post) for post in posts]







import json
import os
import hashlib
from typing import Optional, Dict, List
from groq import Groq
import dotenv
import datetime
import time
import random

# --- Load environment variables ---
dotenv.load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load multiple Groq API keys (cleaned)
GROQ_API_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEYS", "").split(",") if k.strip()]

if not GROQ_API_KEYS:
    raise ValueError("[AI] No Groq API keys found in GROQ_API_KEYS environment variable")

# Configuration
MAX_DAILY_TOKENS = 500000       # ← increased significantly; adjust to your real limit
TOKEN_SAFETY_MARGIN = 300
TOKENS_ESTIMATE = 1800             # fallback when real usage not available

# Usage tracking files
USAGE_FILE = os.path.join(BASE_DIR, "api_usage.json")
RESET_FILE = os.path.join(BASE_DIR, "last_reset.txt")

# --- Load classification prompt ---
PROMPT_FILE = os.path.join(BASE_DIR, "commission_filter.txt")
if os.path.exists(PROMPT_FILE):
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
    print("[AI] Loaded SYSTEM_PROMPT from file.")
else:
    SYSTEM_PROMPT = "Classify if this is a commission request. Return JSON."
    print("[AI] Prompt file not found → using fallback prompt.")

# --- Confidence thresholds ---
CONFIDENCE_HIGH = 0.80
CONFIDENCE_MEDIUM = 0.50
CONFIDENCE_LOW = 0.20

# --- Buyer keywords for pre-filtering (Stage 1) ---
BUYER_KEYWORDS = [
    "looking for artist", "looking to commission", "looking to comm",
    "need artist", "need to commission", "want to commission", "wanna commission",
    "hiring artist", "seeking artist", "seeking animator",
    "someone to commission", "someone to comm", "anyone know an artist",
    "need to find artist", "trying to find artist", "might commission",
    "going to commission", "willing to commission", "can someone draw",
    "need drawn", "want drawn",
]

# --- Seller keywords → HARD REJECT ---
SELLER_KEYWORDS = [
    "commissions open", "comms open", "work slots open", "slots open",
    "available services", "taking commissions", "my commissions", "my comms",
    "my rates", "price sheet", "commission sheet", "portfolio",
    "check my portfolio", "vgen", "ko-fi", "gumroad",
    "finished commission", "completed commission", "i did for", "i made for",
]

# --- Buyer verb gate (MANDATORY) ---
BUYER_VERBS = ["need", "looking", "want", "seeking", "hiring"]

# --- Utility functions ---
def generate_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def quick_keyword_filter(text: str) -> Optional[str]:
    text_lower = text.lower()
    if any(keyword in text_lower for keyword in SELLER_KEYWORDS):
        return "seller"
    if not any(verb in text_lower for verb in BUYER_VERBS):
        return None
    if any(keyword in text_lower for keyword in BUYER_KEYWORDS):
        return "buyer"
    return None

def detect_prompt_injection(text: str) -> bool:
    injection_patterns = [
        "ignore previous", "new instructions", "system:", "assistant:",
        "ignore all", "forget everything", "override", "disregard",
        "you are now", "new role", "act as", "jailbreak",
    ]
    text_lower = text.lower()
    if sum(1 for p in injection_patterns if p in text_lower) >= 2:
        return True
    high_risk = ["ignore previous instructions", "system: you are", "forget your role"]
    return any(p in text_lower for p in high_risk)

# --- API Usage Management ---
if os.path.exists(USAGE_FILE):
    with open(USAGE_FILE, "r") as f:
        api_usage = json.load(f)
else:
    api_usage = {key: 0 for key in GROQ_API_KEYS}

def save_usage():
    with open(USAGE_FILE, "w") as f:
        json.dump(api_usage, f)

def reset_daily_usage():
    today = datetime.date.today().isoformat()
    if os.path.exists(RESET_FILE):
        with open(RESET_FILE, "r") as f:
            last_reset = f.read().strip()
        if last_reset == today:
            return
    for key in api_usage:
        api_usage[key] = 0
    save_usage()
    with open(RESET_FILE, "w") as f:
        f.write(today)
    print("[AI] Daily API usage reset.")

# --- Main classification function ---
def classify_post(text: str, use_two_stage: bool = True) -> Optional[Dict]:
    text = text.strip()
    if not text:
        return None

    reset_daily_usage()

    content_hash = generate_content_hash(text)

    # Stage 1: Prompt injection check
    if detect_prompt_injection(text):
        return {
            "is_commission": False,
            "confidence": 0.0,
            "reason": "Potential prompt injection detected",
            "content_hash": content_hash,
        }

    # Stage 1: Keyword filtering
    if use_two_stage:
        result_stage1 = quick_keyword_filter(text)
        if result_stage1 == "seller":
            return {
                "is_commission": False,
                "confidence": 0.85,
                "reason": "Artist advertising or self-promotion detected",
                "content_hash": content_hash,
            }

    # Prepare keys — shuffle for fairer distribution
    available_keys = list(GROQ_API_KEYS)
    random.shuffle(available_keys)

    # Temporary blacklist for keys that hit rate limit during THIS classification
    blacklisted = set()

    max_attempts = len(GROQ_API_KEYS) * 2
    attempt = 0

    while attempt < max_attempts:
        attempt += 1

        # Select next usable key (least used among non-blacklisted)
        key = None
        candidates = []
        for k in available_keys:
            if k not in blacklisted:
                used = api_usage.get(k, 0)
                if used + TOKENS_ESTIMATE + TOKEN_SAFETY_MARGIN <= MAX_DAILY_TOKENS:
                    candidates.append((used, k))

        if candidates:
            candidates.sort()  # sort by usage (least used first)
            key = candidates[0][1]

        if not key:
            print(f"[AI] No viable key remaining (attempt {attempt})")
            break

        print(f"[AI] Attempt {attempt}/{max_attempts} — using key ...{key[-6:]} (tracked usage: {api_usage.get(key, 0)})")

        client = Groq(api_key=key)

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.0,
                max_tokens=150,
                top_p=1.0,
            )

            # Update real usage
            usage = response.usage
            tokens_used = usage.total_tokens if usage and hasattr(usage, "total_tokens") else TOKENS_ESTIMATE
            api_usage[key] = api_usage.get(key, 0) + tokens_used
            save_usage()
            print(f"[AI] Key ...{key[-6:]} success — used ~{tokens_used} tokens → now {api_usage[key]}")

            # Parse response
            raw_output = response.choices[0].message.content.strip()
            if raw_output.startswith("```"):
                raw_output = "\n".join(
                    line for line in raw_output.split("\n") if not line.startswith("```")
                )
                if raw_output.lower().startswith(("json", "```json")):
                    raw_output = raw_output[raw_output.find("{"):].strip()

            result = json.loads(raw_output)

            # Validate and normalize
            confidence = result.get("confidence", 0.5)
            if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                confidence = 0.5

            result = {
                "is_commission": bool(result.get("is_commission", False)),
                "confidence": float(confidence),
                "reason": result.get("reason", "No reason provided"),
                "content_hash": content_hash,
            }

            # FINAL safety net: detect self-promotion even if LLM says yes
            if result["is_commission"]:
                seller_self_refs = [
                    "my commissions", "my comms", "my work", "my art",
                    "i offer", "dm me for", "message me for"
                ]
                if any(p in text.lower() for p in seller_self_refs):
                    result["is_commission"] = False
                    result["confidence"] = 0.1
                    result["reason"] = "Detected self-promotion / artist advertising"

            return result

        except Exception as e:
            err_str = str(e).lower()
            if "rate_limit" in err_str or "429" in err_str:
                print(f"[AI] Rate limit hit for key ...{key[-6:]} — blacklisting for this call")
                blacklisted.add(key)
                time.sleep(1.0 + attempt * 0.8)  # gentle backoff: ~1s → 2.6s → 4.2s...
                continue
            else:
                print(f"[AI] Error with key ...{key[-6:]}: {e}")
                return None

    print("[AI] ❌ Exhausted all attempts — could not classify post")
    return None

def classify_batch(posts: List[str], max_workers: int = 3) -> List[Optional[Dict]]:
    # For now — simple sequential; add ThreadPoolExecutor later if needed
    return [classify_post(post) for post in posts]


# Optional: small test / debug block
if __name__ == "__main__":
    sample_text = "looking for an artist to commission a dragon character, budget $80"
    result = classify_post(sample_text)
    print("\nResult:")
    print(json.dumps(result, indent=2))

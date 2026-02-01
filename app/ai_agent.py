import json
import os
import hashlib
from typing import Optional, Dict
from groq import Groq
from .config import get_env

# Load Groq API Key
GROQ_API_KEY = get_env("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Load classification prompt
PROMPT_FILE = "commission_filter.txt"

if os.path.exists(PROMPT_FILE):
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
else:
    print("[AI] Warning: commission_filter.txt not found, using fallback prompt")
    SYSTEM_PROMPT = """You are a strict classifier for commission detection.
Determine if the author is SEEKING TO COMMISSION an artist.
ACCEPT: User wants to hire/commission artist
REJECT: Artist advertising, portfolio sharing, general discussion
Output JSON: {"is_commission": bool, "confidence": float, "reason": str}"""

# Confidence thresholds
CONFIDENCE_HIGH = 0.80      # Auto-accept
CONFIDENCE_MEDIUM = 0.50    # Accept but log for review
CONFIDENCE_LOW = 0.50       # Reject threshold

# Buyer keywords for pre-filtering (Stage 1)
BUYER_KEYWORDS = [
    "looking for artist", "need artist", "hiring artist", "seeking artist",
    "looking to commission", "need to commission", "want to commission",
    "looking to comm", "need to comm", "want to comm", "wanna commission",
    "anyone know", "who does", "recommendations", "artist recommendations",
    "drop your portfolio", "if you're an artist", "any artist",
    "need art", "want art", "commission me", "draw for me"
]

# Seller keywords that indicate artist advertising (auto-reject in stage 1)
SELLER_KEYWORDS = [
    "commissions open", "comms open", "i'm open for", "slots available",
    "taking commissions", "my commissions", "commission sheet",
    "commission info", "dm for prices", "check my portfolio",
    "my art", "finished commission", "completed commission"
]


def generate_content_hash(text: str) -> str:
    """Generate SHA-256 hash of post content for deduplication"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def quick_keyword_filter(text: str) -> Optional[str]:
    """
    Stage 1: Fast keyword-based pre-filtering
    Returns: "buyer" if likely commission-seeking, "seller" if likely advertising, None if unclear
    """
    text_lower = text.lower()
    
    # Check for seller indicators first (higher priority)
    seller_matches = sum(1 for keyword in SELLER_KEYWORDS if keyword in text_lower)
    buyer_matches = sum(1 for keyword in BUYER_KEYWORDS if keyword in text_lower)
    
    # Strong seller signals
    if seller_matches >= 2 or any(phrase in text_lower for phrase in ["my commissions", "dm for", "slots open"]):
        return "seller"
    
    # Strong buyer signals
    if buyer_matches >= 2 or any(phrase in text_lower for phrase in ["looking for artist", "need artist", "hiring"]):
        return "buyer"
    
    # Unclear - needs LLM classification
    return None


def detect_prompt_injection(text: str) -> bool:
    """Enhanced prompt injection detection"""
    injection_patterns = [
        "ignore previous", "new instructions", "system:", "assistant:",
        "ignore all", "forget everything", "new task:", "override",
        "disregard", "you are now", "new role", "act as", "jailbreak",
        "pretend you", "from now on", "instead of"
    ]
    
    text_lower = text.lower()
    
    # Check for multiple injection patterns (more reliable)
    matches = sum(1 for pattern in injection_patterns if pattern in text_lower)
    
    # Flag if 2+ patterns detected or certain high-risk phrases
    if matches >= 2:
        return True
    
    high_risk = ["ignore previous instructions", "system: you are", "forget your role"]
    return any(phrase in text_lower for phrase in high_risk)


def classify_post(text: str, use_two_stage: bool = True) -> Optional[Dict]:
    """
    Classify if a post is a commission request using Groq API.
    
    Args:
        text: Post content to classify
        use_two_stage: Enable two-stage classification (keyword pre-filter + LLM)
    
    Returns:
        dict with keys: is_commission, confidence, reason, content_hash
        None if classification fails
    """
    if not text or not text.strip():
        return None
    
    # Generate content hash for deduplication
    content_hash = generate_content_hash(text)
    
    # Detect prompt injection
    if detect_prompt_injection(text):
        print(f"[AI] ⚠️  Potential prompt injection detected")
        return {
            "is_commission": False,
            "confidence": 0.0,
            "reason": "Potential prompt injection detected",
            "content_hash": content_hash
        }
    
    # Stage 1: Quick keyword filter (optional but recommended)
    if use_two_stage:
        filter_result = quick_keyword_filter(text)
        
        if filter_result == "seller":
            print(f"[AI] 🚫 Quick filter: Artist advertising (skipping LLM)")
            return {
                "is_commission": False,
                "confidence": 0.85,
                "reason": "Artist advertising services (keyword-based filter)",
                "content_hash": content_hash
            }
        elif filter_result == "buyer":
            print(f"[AI] ✅ Quick filter: Likely buyer (confirming with LLM)")
        else:
            print(f"[AI] 🔍 Quick filter: Unclear (using LLM)")
    
    # Stage 2: LLM Classification
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.0,
            max_tokens=150,
            top_p=1.0,
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if raw_output.startswith("```"):
            lines = raw_output.split("\n")
            raw_output = "\n".join(line for line in lines if not line.startswith("```"))
            if raw_output.startswith("json"):
                raw_output = raw_output[4:].strip()
        
        # Parse JSON
        result = json.loads(raw_output)
        
        # Validate schema
        if not isinstance(result.get("is_commission"), bool):
            print("[AI] ❌ Invalid schema: 'is_commission' must be boolean")
            return None
        
        # Ensure confidence is present and valid
        confidence = result.get("confidence")
        if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
            print(f"[AI] ⚠️  Invalid confidence value, defaulting to 0.5")
            confidence = 0.5
        
        result["confidence"] = float(confidence)
        
        # Ensure reason is present
        if not isinstance(result.get("reason"), str):
            result["reason"] = "No reason provided"
        
        # Add content hash
        result["content_hash"] = content_hash
        
        # Log confidence level
        is_comm = result["is_commission"]
        conf = result["confidence"]
        
        if is_comm and conf >= CONFIDENCE_HIGH:
            print(f"[AI] ✅ HIGH confidence ({conf:.2f}): Commission seeking")
        elif is_comm and conf >= CONFIDENCE_MEDIUM:
            print(f"[AI] ⚠️  MEDIUM confidence ({conf:.2f}): Commission seeking (review recommended)")
        elif is_comm:
            print(f"[AI] 🔍 LOW confidence ({conf:.2f}): Commission seeking (uncertain)")
        else:
            print(f"[AI] 🚫 Not commission ({conf:.2f}): {result.get('reason', 'N/A')[:50]}")
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"[AI] ❌ JSON parse error: {e}")
        print(f"[AI] Raw output (first 200 chars): {raw_output[:200]}")
        return None
    
    except Exception as e:
        print(f"[AI] ❌ Classification failed: {type(e).__name__}: {e}")
        return None


def classify_batch(posts: list[str], max_workers: int = 3) -> list[Optional[Dict]]:
    """
    Classify multiple posts concurrently (future enhancement)
    
    Args:
        posts: List of post texts
        max_workers: Maximum concurrent API calls
    
    Returns:
        List of classification results (same order as input)
    """
    # TODO: Implement concurrent classification using asyncio or ThreadPoolExecutor
    # For now, just classify sequentially
    return [classify_post(post) for post in posts]
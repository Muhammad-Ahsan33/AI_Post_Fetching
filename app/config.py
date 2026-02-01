import os
import dotenv

# Load environment variables
dotenv.load_dotenv()


def get_env(key: str, required: bool = True, default=None):
    """
    Safely get environment variable with validation
    
    Args:
        key: Environment variable name
        required: Whether the variable is required
        default: Default value if not found
    
    Returns:
        Environment variable value or default
    
    Raises:
        RuntimeError: If required variable is missing
    """
    value = os.getenv(key, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


# ═══════════════════════════════════════════════════════════════════════════
# API CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Groq API (for LLM classification)
GROQ_API_KEY = get_env("GROQ_API_KEY")

# Discord Webhook (for notifications)
DISCORD_WEBHOOK_URL = get_env("DISCORD_WEBHOOK_URL")


# ═══════════════════════════════════════════════════════════════════════════
# SCHEDULER CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# How often to fetch new posts (in hours) 
# Default: 2 hours
FETCH_INTERVAL_HOURS = int(get_env("FETCH_INTERVAL_HOURS", required=False, default="2"))

# Recency window for filtering posts (in seconds)
# Should match FETCH_INTERVAL_HOURS to avoid gaps or overlaps
# Default: Automatically calculated from FETCH_INTERVAL_HOURS
RECENCY_WINDOW_SECONDS = int(get_env(
    "RECENCY_WINDOW_SECONDS", 
    required=False, 
    default=str(FETCH_INTERVAL_HOURS * 3600)
))


# ═══════════════════════════════════════════════════════════════════════════
# BLUESKY API CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Maximum posts to fetch per keyword
# Default: 100
MAX_POSTS_PER_KEYWORD = int(get_env("MAX_POSTS_PER_KEYWORD", required=False, default="100"))

# Rate limit delay between keyword requests (seconds)
# Default: 1.5 seconds
BLUESKY_RATE_LIMIT_DELAY = float(get_env("BLUESKY_RATE_LIMIT_DELAY", required=False, default="1.5"))


# ═══════════════════════════════════════════════════════════════════════════
# CLASSIFICATION CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Enable two-stage classification (keyword pre-filter + LLM)
# Default: True
USE_TWO_STAGE_CLASSIFICATION = get_env("USE_TWO_STAGE_CLASSIFICATION", required=False, default="true").lower() == "true"

# Confidence thresholds
CONFIDENCE_THRESHOLD_HIGH = float(get_env("CONFIDENCE_THRESHOLD_HIGH", required=False, default="0.80"))
CONFIDENCE_THRESHOLD_MEDIUM = float(get_env("CONFIDENCE_THRESHOLD_MEDIUM", required=False, default="0.50"))
CONFIDENCE_THRESHOLD_LOW = float(get_env("CONFIDENCE_THRESHOLD_LOW", required=False, default="0.50"))


# ═══════════════════════════════════════════════════════════════════════════
# STORAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Path to posts storage file
DATA_FILE = get_env("DATA_FILE", required=False, default="data/posts.json")

# Maximum age of posts to keep in storage (days)
# Older posts are archived/pruned
# Default: 30 days
MAX_STORAGE_AGE_DAYS = int(get_env("MAX_STORAGE_AGE_DAYS", required=False, default="30"))

# Maximum number of posts to keep in storage
# Prevents unlimited growth
# Default: 10,000 posts
MAX_STORAGE_SIZE = int(get_env("MAX_STORAGE_SIZE", required=False, default="10000"))


# ═══════════════════════════════════════════════════════════════════════════
# LOGGING CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = get_env("LOG_LEVEL", required=False, default="INFO")

# Log file path (optional - if not set, logs to console only)
LOG_FILE = get_env("LOG_FILE", required=False, default=None)


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE FLAGS
# ═══════════════════════════════════════════════════════════════════════════

# Enable content-based deduplication (using SHA-256 hash)
ENABLE_CONTENT_DEDUPLICATION = get_env("ENABLE_CONTENT_DEDUPLICATION", required=False, default="true").lower() == "true"

# Enable automatic storage pruning
ENABLE_STORAGE_PRUNING = get_env("ENABLE_STORAGE_PRUNING", required=False, default="true").lower() == "true"

# Enable detailed logging in Discord notifications
DISCORD_VERBOSE_NOTIFICATIONS = get_env("DISCORD_VERBOSE_NOTIFICATIONS", required=False, default="false").lower() == "true"


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def validate_config():
    """Validate configuration and print warnings"""
    issues = []
    
    # Check if recency window matches fetch interval
    expected_window = FETCH_INTERVAL_HOURS * 3600
    if RECENCY_WINDOW_SECONDS != expected_window:
        issues.append(
            f"⚠️  Recency window ({RECENCY_WINDOW_SECONDS}s) doesn't match fetch interval "
            f"({FETCH_INTERVAL_HOURS}h = {expected_window}s). This may cause gaps or overlaps."
        )
    
    # Check confidence thresholds
    if not (0 <= CONFIDENCE_THRESHOLD_LOW <= CONFIDENCE_THRESHOLD_MEDIUM <= CONFIDENCE_THRESHOLD_HIGH <= 1):
        issues.append(
            f"⚠️  Invalid confidence thresholds: LOW={CONFIDENCE_THRESHOLD_LOW}, "
            f"MEDIUM={CONFIDENCE_THRESHOLD_MEDIUM}, HIGH={CONFIDENCE_THRESHOLD_HIGH}"
        )
    
    # Print issues
    if issues:
        print("\n" + "="*80)
        print("CONFIGURATION WARNINGS:")
        print("="*80)
        for issue in issues:
            print(issue)
        print("="*80 + "\n")
    
    return len(issues) == 0


# Run validation on import
if __name__ != "__main__":
    validate_config()
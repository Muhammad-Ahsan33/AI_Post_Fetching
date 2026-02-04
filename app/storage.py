import json
import os
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
# from .config import DATA_FILE
import os
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Configuration
MAX_STORAGE_AGE_DAYS = 30  # Archive posts older than this
MAX_STORAGE_SIZE = 10000    # Maximum posts to keep

DATA_FILE = os.getenv("DATA_FILE", default="data/posts.json")

def load_data() -> List[Dict]:
    """Load stored posts from JSON file"""
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
            if not content:
                return []
            
            data = json.loads(content)
            
            # Validate data structure
            if not isinstance(data, list):
                print("[Storage] Warning: Invalid data structure, resetting")
                return []
            
            return data

    except json.JSONDecodeError as e:
        print(f"[Storage] ❌ Invalid JSON detected: {e}")
        print("[Storage] Creating backup and resetting storage")
        
        # Backup corrupted file
        if os.path.exists(DATA_FILE):
            backup_path = f"{DATA_FILE}.backup.{int(datetime.now().timestamp())}"
            os.rename(DATA_FILE, backup_path)
            print(f"[Storage] Corrupted file backed up to: {backup_path}")
        
        return []
    
    except Exception as e:
        print(f"[Storage] ❌ Unexpected error loading data: {e}")
        return []


def save_data(data: List[Dict]) -> None:
    """Save posts to JSON file with atomic write"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        # Write to temporary file first (atomic operation)
        tmp_file = DATA_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Atomic replace (safe on crashes)
        os.replace(tmp_file, DATA_FILE)
        
        print(f"[Storage] ✅ Saved {len(data)} posts")
        
    except Exception as e:
        print(f"[Storage] ❌ Error saving data: {e}")


def is_duplicate(posts: List[Dict], url: str, content_hash: Optional[str] = None) -> bool:
    """
    Check if post is duplicate using URL and/or content hash
    
    Args:
        posts: List of stored posts
        url: Post URL
        content_hash: SHA-256 hash of post content (optional but recommended)
    
    Returns:
        True if duplicate found, False otherwise
    """
    for post in posts:
        # Check URL match (exact)
        if post.get("url") == url:
            return True
        
        # Check content hash match (detects reposts with different URLs)
        if content_hash and post.get("ai", {}).get("content_hash") == content_hash:
            print(f"[Storage] 🔍 Duplicate content detected (different URL)")
            return True
    
    return False


def prune_old_posts(posts: List[Dict], max_age_days: int = MAX_STORAGE_AGE_DAYS) -> List[Dict]:
    """
    Remove posts older than max_age_days
    
    Args:
        posts: List of posts
        max_age_days: Maximum age in days
    
    Returns:
        Filtered list of recent posts
    """
    if not posts:
        return []
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    
    # Count posts before pruning
    original_count = len(posts)
    
    # Filter posts
    recent_posts = []
    for post in posts:
        # Try to get timestamp from AI classification data or assume it's recent
        timestamp_str = post.get("ai", {}).get("timestamp")
        
        if timestamp_str:
            try:
                post_date = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if post_date >= cutoff_date:
                    recent_posts.append(post)
            except (ValueError, AttributeError):
                # Keep post if timestamp parsing fails (assume recent)
                recent_posts.append(post)
        else:
            # No timestamp, keep it (assume recent)
            recent_posts.append(post)
    
    pruned_count = original_count - len(recent_posts)
    if pruned_count > 0:
        print(f"[Storage] 🗑️  Pruned {pruned_count} old posts (>{max_age_days} days)")
    
    return recent_posts


def limit_storage_size(posts: List[Dict], max_size: int = MAX_STORAGE_SIZE) -> List[Dict]:
    """
    Limit storage to most recent N posts
    
    Args:
        posts: List of posts
        max_size: Maximum number of posts to keep
    
    Returns:
        List limited to max_size most recent posts
    """
    if len(posts) <= max_size:
        return posts
    
    # Sort by timestamp (if available) or keep last N
    # For now, just keep last N (assumes posts are added chronologically)
    removed_count = len(posts) - max_size
    print(f"[Storage] ⚠️  Storage limit reached, removing {removed_count} oldest posts")
    
    return posts[-max_size:]


def add_post(posts: List[Dict], new_post: Dict) -> List[Dict]:
    """
    Add new post with automatic deduplication and pruning
    
    Args:
        posts: Existing posts
        new_post: New post to add
    
    Returns:
        Updated posts list
    """
    # Add timestamp if not present
    if "ai" not in new_post:
        new_post["ai"] = {}
    
    if "timestamp" not in new_post["ai"]:
        new_post["ai"]["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    # Check for duplicates
    url = new_post.get("url")
    content_hash = new_post.get("ai", {}).get("content_hash")
    
    if is_duplicate(posts, url, content_hash):
        print(f"[Storage] 🚫 Duplicate detected, skipping")
        return posts
    
    # Add post
    posts.append(new_post)
    
    # Prune old posts
    posts = prune_old_posts(posts)
    
    # Limit storage size
    posts = limit_storage_size(posts)
    
    return posts


def get_recent_posts(posts: List[Dict], hours: int = 24) -> List[Dict]:
    """
    Get posts from the last N hours
    
    Args:
        posts: All posts
        hours: Number of hours to look back
    
    Returns:
        Filtered list of recent posts
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = []
    
    for post in posts:
        timestamp_str = post.get("ai", {}).get("timestamp")
        if timestamp_str:
            try:
                post_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if post_time >= cutoff:
                    recent.append(post)
            except (ValueError, AttributeError):
                continue
    
    return recent


def export_to_csv(posts: List[Dict], output_file: str = "data/posts_export.csv") -> None:
    """
    Export posts to CSV for analysis
    
    Args:
        posts: Posts to export
        output_file: Output CSV file path
    """
    import csv
    
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            if not posts:
                return
            
            # Define CSV columns
            fieldnames = ["timestamp", "author", "url", "text", "is_commission", "confidence", "reason"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for post in posts:
                ai_data = post.get("ai", {})
                writer.writerow({
                    "timestamp": ai_data.get("timestamp", ""),
                    "author": post.get("author", ""),
                    "url": post.get("web_url", post.get("url", "")),
                    "text": post.get("text", "")[:500],  # Limit text length
                    "is_commission": ai_data.get("is_commission", False),
                    "confidence": ai_data.get("confidence", 0.0),
                    "reason": ai_data.get("reason", "")
                })
        
        print(f"[Storage] ✅ Exported {len(posts)} posts to {output_file}")
        
    except Exception as e:
        print(f"[Storage] ❌ Export failed: {e}")
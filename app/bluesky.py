import requests
import time
from typing import List, Dict, Optional
from datetime import datetime, timezone
# from .config import MAX_POSTS_PER_KEYWORD
import os
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Load max posts per keyword from config or use default
MAX_POSTS_PER_KEYWORD = int(os.getenv("MAX_POSTS_PER_KEYWORD"))

BLUESKY_API_URL = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts"

def fetch_posts(keyword: str, max_posts: int = None) -> List[Dict]:
    """
    Fetch posts from BlueSky API for a given keyword with pagination support.
    
    Args:
        keyword: Search term
        max_posts: Maximum posts to fetch (uses config default if None)
        
    Returns:
        List of post dictionaries
    """
    if max_posts is None:
        max_posts = MAX_POSTS_PER_KEYWORD
    
    all_posts = []
    cursor = None
    pages_fetched = 0
    max_pages = max(1, (max_posts + 49) // 50)  # Calculate pages needed (50 posts per page)
    
    while len(all_posts) < max_posts and pages_fetched < max_pages:
        params = {
            "q": keyword,
            "limit": min(50, max_posts - len(all_posts)),  # Don't fetch more than needed
            "sort": "latest",
            "lang": "en"
        }
        
        if cursor:
            params["cursor"] = cursor
        
        try:
            response = requests.get(BLUESKY_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            posts = data.get("posts", [])
            if not posts:
                break  # No more posts available
            
            all_posts.extend(posts)
            pages_fetched += 1
            
            # Get cursor for next page
            cursor = data.get("cursor")
            if not cursor:
                break  # No more pages
            
            # Rate limiting between pages (only if fetching another page)
            if len(all_posts) < max_posts and cursor:
                time.sleep(0.5)  # Shorter delay between pages of same keyword
                
        except requests.exceptions.RequestException as e:
            print(f"[BlueSky] Error fetching '{keyword}' (page {pages_fetched + 1}): {e}")
            break
        except Exception as e:
            print(f"[BlueSky] Unexpected error for '{keyword}': {e}")
            break
    
    # Trim to exact max_posts if we got more
    all_posts = all_posts[:max_posts]
    
    if all_posts:
        print(f"[BlueSky] '{keyword}': {len(all_posts)} posts ({pages_fetched} page(s))")
    
    return all_posts


def fetch_all(keywords: List[str]) -> List[Dict]:
    """
    Fetch posts for all keywords with rate limiting.
    
    Args:
        keywords: List of search terms
        
    Returns:
        Combined list of all posts
    """
    print(f"[BlueSky] Fetching posts for {len(keywords)} keywords...")
    
    all_posts = []
    for i, keyword in enumerate(keywords, 1):
        posts = fetch_posts(keyword)
        all_posts.extend(posts)
        
        # Rate limiting between keywords (longer delay)
        if i < len(keywords):
            time.sleep(1.5)
    
    print(f"[BlueSky] Total posts fetched: {len(all_posts)}")
    return all_posts


def filter_recent_posts(posts: List[Dict], seconds: int) -> List[Dict]:
    """
    Keep only posts created within the last N seconds.
    
    Args:
        posts: List of post dictionaries
        seconds: Time window in seconds (e.g., 7200 for 2 hours)
        
    Returns:
        Filtered list of recent posts
    """
    now = datetime.now(timezone.utc)
    recent_posts = []

    for post in posts:
        # Try nested structure first, then fallback
        created_at = post.get("createdAt") or post.get("record", {}).get("createdAt")
        
        if not created_at:
            continue  # Skip posts without timestamp

        try:
            # Parse ISO 8601 timestamp
            post_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            
            # Check if within time window
            age_seconds = (now - post_time).total_seconds()
            
            if age_seconds <= seconds:
                recent_posts.append(post)
                
        except (ValueError, AttributeError):
            # Skip posts with invalid timestamps
            continue

    print(f"[BlueSky] Filtered to {len(recent_posts)} posts within last {seconds}s ({seconds//3600}h)")
    return recent_posts


def fetch_posts_since_timestamp(keyword: str, since: datetime, max_posts: int = 200) -> List[Dict]:
    """
    Fetch posts for a keyword, stopping when we reach posts older than 'since'.
    This is more efficient than fetching all posts and filtering.
    
    Args:
        keyword: Search term
        since: Only fetch posts newer than this timestamp
        max_posts: Safety limit to prevent infinite fetching
        
    Returns:
        List of post dictionaries newer than 'since'
    """
    all_posts = []
    cursor = None
    found_old_post = False
    
    while not found_old_post and len(all_posts) < max_posts:
        params = {
            "q": keyword,
            "limit": 100,
            "sort": "latest",
            "lang": "en"
        }
        
        if cursor:
            params["cursor"] = cursor
        
        try:
            response = requests.get(BLUESKY_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            posts = data.get("posts", [])

            if not posts:
                break
            
            # Check each post's timestamp
            for post in posts:
                created_at = post.get("createdAt") or post.get("indexedAt") or post.get("record", {}).get("createdAt")
                
                
                if created_at:
                    try:
                        post_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        
                        if post_time >= since:
                            all_posts.append(post)
                        else:
                            # Found a post older than our cutoff, stop fetching
                            found_old_post = True
                            break
                    except (ValueError, AttributeError):
                        continue
            
            # Get cursor for next page
            cursor = data.get("cursor")
            if not cursor:
                break
            
            # Rate limiting
            if not found_old_post and cursor:
                time.sleep(0.5)
                
        except Exception as e:
            print(f"[BlueSky] Error in timestamp-based fetch for '{keyword}': {e}")
            break
    
    if all_posts:
        print(f"[BlueSky] '{keyword}': {len(all_posts)} posts since {since.isoformat()}")
    
    return all_posts


def fetch_all_since_timestamp(keywords: List[str], since: datetime) -> List[Dict]:
    """
    Fetch posts for all keywords since a specific timestamp.
    More efficient than fetching max posts and filtering.
    
    Args:
        keywords: List of search terms
        since: Only fetch posts newer than this timestamp
        
    Returns:
        Combined list of all posts
    """
    print(f"[BlueSky] Fetching posts since {since.isoformat()}...")
    print(f"[BlueSky] Fetching posts for {len(keywords)} keywords...")
    
    all_posts = []
    for i, keyword in enumerate(keywords, 1):
        posts = fetch_posts_since_timestamp(keyword, since)
        all_posts.extend(posts)
        
        # Rate limiting between keywords
        if i < len(keywords):
            time.sleep(1.5)
    
    print(f"[BlueSky] Total posts fetched: {len(all_posts)}")
    return all_posts


def at_uri_to_web_url(at_uri: str, username: str) -> str:
    """
    Convert AT Protocol URI to web URL.
    
    Example:
      at://did:plc:xxx/app.bsky.feed.post/abc123
      → https://bsky.app/profile/username.bsky.social/post/abc123
    
    Args:
        at_uri: AT Protocol URI (e.g., at://did:xxx/app.bsky.feed.post/123)
        username: User's handle (e.g., "alice.bsky.social")
        
    Returns:
        Web-accessible URL
    """
    try:
        # Extract post ID (last segment of URI)
        post_id = at_uri.split("/")[-1]
        return f"https://bsky.app/profile/{username}/post/{post_id}"
    except Exception as e:
        print(f"[BlueSky] URL conversion error: {e}")
        return at_uri  # Fallback to original

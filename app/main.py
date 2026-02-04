from requests import post
from .keywords import KEYWORDS
from .bluesky import fetch_all, fetch_all_since_timestamp, filter_recent_posts, at_uri_to_web_url
from .ai_agent import classify_post
from .storage import load_data, save_data, add_post, is_duplicate
from .discord_notify import send_batch_notification
# from .config import FETCH_INTERVAL_HOURS
from datetime import datetime, timezone, timedelta
import traceback
import os
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Load fetch interval from config or use default
FETCH_INTERVAL_HOURS = int(os.getenv("FETCH_INTERVAL_HOURS"))
# Calculate recency window from config
RECENCY_WINDOW_SECONDS = FETCH_INTERVAL_HOURS * 3600  # Convert hours to seconds
# RECENCY_WINDOW_SECONDS = 100

# Choose fetching strategy
USE_TIMESTAMP_FETCH = True  # Set to False to use old method (fetch all + filter)


def normalize(post):
    """
    Normalize BlueSky post structure to internal format
    
    Args:
        post: Raw post from BlueSky API
    
    Returns:
        Normalized post dict
    """
    return {
        "url": post.get("uri"),
        "text": post.get("record", {}).get("text", ""),
        "author": post.get("author", {}).get("handle"),
        "location": post.get("author", {}).get("location")
    }


def run_pipeline():
    """Main pipeline: fetch → filter → classify → store → notify"""
    
    print("\n" + "="*80)
    print("[Pipeline] 🚀 Starting fetch cycle...")
    print("="*80)
    
    try:
        # Load existing posts
        stored = load_data()
        print(f"[Pipeline] 📚 Loaded {len(stored)} existing posts from storage")
        
        # Fetch posts using selected strategy
        if USE_TIMESTAMP_FETCH:
            # Strategy 1: Timestamp-based fetching (more efficient)
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=RECENCY_WINDOW_SECONDS)
            print("Cutoff time = ", cutoff_time)
            print(f"[Pipeline] 🔍 Fetching posts since {cutoff_time.strftime('%Y-%m-%d %H:%M:%S UTC')}...")
            recent_posts = fetch_all_since_timestamp(KEYWORDS, since=cutoff_time)
            print(f"[Pipeline] ✅ Fetched {len(recent_posts)} recent posts")
            print("This is Strategy 1 timestamp-based fetching")
        else:
            # Strategy 2: Fetch all + filter (old method with pagination)
            print(f"[Pipeline] 🔍 Fetching posts for {len(KEYWORDS)} keywords...")
            posts = fetch_all(KEYWORDS)
            print(f"[Pipeline] ✅ Fetched {len(posts)} total posts")
            
            if not posts:
                print("[Pipeline] ⚠️  No posts fetched, ending cycle")
                return
            
            # Filter for recency
            print(f"[Pipeline] ⏰ Filtering for posts from last {FETCH_INTERVAL_HOURS} hours ({RECENCY_WINDOW_SECONDS}s)...")
            recent_posts = filter_recent_posts(posts, seconds=RECENCY_WINDOW_SECONDS)
            print(f"[Pipeline] ✅ {len(recent_posts)} posts are recent")
        
        if not recent_posts:
            print("[Pipeline] ℹ️  No recent posts found, ending cycle")
            return
        
        # Track new qualified posts for batch notification
        new_qualified_posts = []
        processed_count = 0
        duplicate_count = 0
        rejected_count = 0
        error_count = 0
        
        print(f"[Pipeline] 🤖 Processing {len(recent_posts)} recent posts...")
        
        for i, raw in enumerate(recent_posts, 1):
            try:
                # Normalize post structure
                post = normalize(raw)

                # Clean text (IMPORTANT: before checks & classification)
                post["text"] = post["text"].strip()
                
                # Skip invalid posts
                if not post["url"] or not post["text"]:
                    print(f"[Pipeline] [{i}/{len(recent_posts)}] ⚠️  Skipping invalid post (missing URL or text)")
                    error_count += 1
                    continue
                
                # Check for duplicates (URL-based)
                if is_duplicate(stored, post["url"]):
                    print(f"[Pipeline] [{i}/{len(recent_posts)}] 🔄 Duplicate: {post['author']}")
                    duplicate_count += 1
                    continue
                
                # AI Classification
                print(f"[Pipeline] [{i}/{len(recent_posts)}] 🧠 Classifying: {post['author'][:30]}")
                ai_result = classify_post(post["text"], use_two_stage=True)

                
                if not ai_result:
                    print(f"[Pipeline] [{i}/{len(recent_posts)}] ❌ Classification failed")
                    error_count += 1
                    continue
                
                # Check if it's a commission request
                if not ai_result.get("is_commission"):
                    print(f"[Pipeline] [{i}/{len(recent_posts)}] 🚫 Not a commission")
                    rejected_count += 1
                    continue

                confidence = ai_result.get("confidence", 0.0)

                if confidence < 0.90:
                    print(f"[Pipeline] [{i}/{len(recent_posts)}] ⚠️ Low confidence ({confidence:.0%}), skipping")
                    rejected_count += 1
                    continue


                
                # Build web URL
                username = post["author"]
                web_url = at_uri_to_web_url(post["url"], username)
                post["web_url"] = web_url
                
                # Store AI result
                post["ai"] = ai_result
                
                # Add to storage using helper function
                stored = add_post(stored, post)
                new_qualified_posts.append(post)
                
                confidence = ai_result.get("confidence", 0)
                print(f"[Pipeline] [{i}/{len(recent_posts)}] ✅ QUALIFIED ({confidence:.0%}): {post['author']}")
                
                processed_count += 1
                
            except Exception as e:
                print(f"[Pipeline] [{i}/{len(recent_posts)}] ❌ Error processing post: {e}")
                traceback.print_exc()
                error_count += 1
                continue
        
        # Save all changes
        if new_qualified_posts:
            save_data(stored)
            print(f"\n[Pipeline] 💾 Saved {len(new_qualified_posts)} new posts to storage")
            
            # Send batch notification
            try:
                send_batch_notification(new_qualified_posts)
                print(f"[Pipeline] 📤 Sent batch notification to Discord ({len(new_qualified_posts)} posts)")
            except Exception as e:
                print(f"[Pipeline] ❌ Discord notification failed: {e}")
                traceback.print_exc()
        else:
            print("\n[Pipeline] ℹ️  No new qualified posts found")
        
        # Print summary
        print("\n" + "="*80)
        print("[Pipeline] 📊 CYCLE SUMMARY")
        print("="*80)
        if USE_TIMESTAMP_FETCH:
            print(f"Recent posts:        {len(recent_posts)}")
        else:
            print(f"Total fetched:       {len(posts)}")
            print(f"Recent posts:        {len(recent_posts)}")
        print(f"Duplicates:          {duplicate_count}")
        print(f"Rejected:            {rejected_count}")
        print(f"Errors:              {error_count}")
        print(f"✅ NEW QUALIFIED:    {len(new_qualified_posts)}")
        print("="*80 + "\n")
        
    except KeyboardInterrupt:
        print("\n[Pipeline] ⚠️  Interrupted by user")
        raise
    
    except Exception as e:
        print(f"\n[Pipeline] ❌ CRITICAL ERROR: {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    from .scheduler import run_forever
    from flask import Flask
    import threading

    app = Flask(__name__)

    @app.route("/")
    def health():
        return {
            "status": "ok",
            "service": "AI Commission Hunting Agent",
            "uptime": "running"
        }

    def start_pipeline():
        print("""
        ╔═══════════════════════════════════════════════════════════╗
        ║   AI COMMISSION HUNTING AGENT                              ║
        ║   Monitoring BlueSky for commission requests               ║
        ╚═══════════════════════════════════════════════════════════╝
        """)
        try:
            run_forever(run_pipeline)
        except KeyboardInterrupt:
            print("\n[Main] 👋 Shutting down gracefully...")
        except Exception as e:
            print(f"\n[Main] ❌ Fatal error: {e}")
            traceback.print_exc()

    # Run pipeline in background thread
    threading.Thread(target=start_pipeline, daemon=True).start()

    # Run web server (required by Render)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


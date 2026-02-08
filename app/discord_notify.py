import requests
from typing import List, Dict
# from .config import DISCORD_WEBHOOK_URL
import os
import dotenv

# Load environment variables
dotenv.load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def sanitize(text: str) -> str:
    """Remove Discord mention triggers"""
    return text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

def send_notification(post: Dict):
    """Send a single post notification (legacy/fallback)"""
    payload = {
        "content": sanitize(
            f"🎨 **New Commission Found**\n"
            f"👤 {post['author']}\n"
            f"📍 {post.get('location', 'Unknown')}\n"
            f"🔗 {post.get('web_url', post['url'])}\n\n"
            f"{post['text'][:900]}"
        )
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print("[Discord] Error sending notification:", e)

def send_batch_notification(posts: List[Dict]):
    """
    Send ONE Discord message containing ALL qualified posts from this fetch cycle.
    Handles Discord's 2000 character limit by splitting into multiple messages if needed.
    """
    if not posts:
        print("Skipping Discord notification: No new posts found.")
        payload = {
            "content": "🎨 **Commission Scan Complete**\n\n❌ No new commission requests found in this cycle."
        }
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print("[Discord] Error sending empty batch notification:", e)
        return

    
    # Build the batch message
    header = f"🎨 **Found {len(posts)} New Commission Request(s)**\n\n"
    
    messages = []
    current_message = header
    
    for i, post in enumerate(posts, 1):
        confidence = post.get("ai", {}).get("confidence", 0)
        
        post_block = (
            f"**#{i}** — {post['author']}\n"
            f"🔗 {post.get('web_url', post['url'])}\n"
            f"📊 Confidence: {confidence:.0%}\n"
            f"💬 {sanitize(post['text'][:200])}...\n"
            f"{'─' * 40}\n\n"
        )
        
        # Check if adding this post would exceed Discord's 2000 char limit
        if len(current_message + post_block) > 1900:
            messages.append(current_message)
            current_message = post_block
        else:
            current_message += post_block
    
    # Add the last message
    if current_message:
        messages.append(current_message)
    
    # Send all messages
    for msg in messages:
        payload = {"content": msg}
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print("[Discord] Error sending batch notification:", e)

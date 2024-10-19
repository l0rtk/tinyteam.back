from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ..database import get_db
import json
from datetime import datetime, timezone
from typing import Optional

router = APIRouter()

def format_post(post):
    """Helper function to format a single post"""
    formatted = dict(post)
    formatted['_id'] = str(formatted['_id'])
    formatted['created_utc'] = datetime.fromtimestamp(formatted['created_utc']).isoformat()
    return formatted

@router.websocket("/ws/keyword_posts/{keyword}")
async def websocket_posts(websocket: WebSocket, keyword: str, subreddit: Optional[str] = Query(None)):
    """
    WebSocket endpoint for receiving live posts for a specific keyword.
    
    This endpoint allows clients to connect via WebSocket and receive updates on posts
    containing the specified keyword. The server will send only new posts since the last message.
    
    To use this endpoint:
    1. Connect to ws://your-server-address/ws/keyword_posts/{keyword}
    2. Send any message to request an update
    3. Receive JSON data containing the latest posts with the specified keyword
    
    Optional query parameter:
    - subreddit: Filter posts by subreddit
    
    Note: This endpoint is not testable via Swagger UI. Use a WebSocket client to interact with it.
    """
    await websocket.accept()
    db = get_db()
    last_timestamp = 0
    
    try:
        while True:
            # Prepare the query
            query = {
                "keyword": keyword.lower(),
                "created_utc": {"$gt": last_timestamp}
            }
            if subreddit:
                query["subreddit"] = subreddit

            # Fetch new posts from the database for the specific keyword
            new_posts = list(db.reddit.find(query).sort("created_utc", -1).limit(100))
            
            if new_posts:
                # Update the last timestamp
                last_timestamp = new_posts[0]["created_utc"]
                
                # Format posts
                formatted_posts = [format_post(p) for p in new_posts]
                
                # Send the new posts to the client
                await websocket.send_text(json.dumps(formatted_posts))
            else:
                # If no new posts, send an empty list
                await websocket.send_text(json.dumps([]))
            
            # Wait for a message from the client (you can adjust the logic here)
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        print(f"Client disconnected from {keyword} posts feed")
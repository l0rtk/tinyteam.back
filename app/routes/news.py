from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ..database import get_db
import json
from datetime import datetime, timezone
from typing import List, Optional

router = APIRouter()

def format_news(news, requested_tickers):
    """Helper function to format a single news article with sentiment"""
    formatted = dict(news)
    formatted['_id'] = str(formatted['_id'])
    formatted['published_utc'] = formatted['published_utc']
    formatted['fetched_at'] = formatted['fetched_at']
    
    # Extract sentiment for requested tickers
    formatted['ticker_sentiment'] = {}
    for insight in formatted.get('insights', []):
        if insight['ticker'] in requested_tickers:
            formatted['ticker_sentiment'] = {
                'sentiment': insight['sentiment'],
                'sentiment_reasoning': insight['sentiment_reasoning']
            }
    
    return formatted

@router.websocket("/ws/ticker_news")
async def websocket_news(
    websocket: WebSocket, 
    tickers: str = Query(..., description="Comma-separated list of stock tickers"),
    limit: int = Query(100, description="Number of news articles to fetch per request")
):
    """
    WebSocket endpoint for receiving live news for multiple stock tickers.
    
    This endpoint allows clients to connect via WebSocket and receive updates on news articles
    related to any of the specified stock tickers. The server will send only new articles since the last message.
    Each article includes a 'ticker_sentiment' field with sentiment information for the requested tickers.
    
    To use this endpoint:
    1. Connect to ws://your-server-address/ws/ticker_news?tickers=AAPL,GOOGL,MSFT
    2. Send any message to request an update
    3. Receive JSON data containing the latest news articles for any of the specified tickers
    
    Query parameters:
    - tickers: Comma-separated list of stock tickers to track (required)
    - limit: Number of news articles to fetch per request (default: 100)
    
    Note: This endpoint is not testable via Swagger UI. Use a WebSocket client to interact with it.
    """
    await websocket.accept()
    db = get_db()
    last_timestamp = datetime.min.replace(tzinfo=timezone.utc).isoformat()
    
    # Split the tickers string into a list
    ticker_list = [t.strip().upper() for t in tickers.split(',')]
    
    try:
        while True:
            # Prepare the query
            query = {
                "insights.ticker": {"$in": ticker_list},
                "published_utc": {"$gt": last_timestamp}
            }

            # Fetch new news articles from the database for any of the specified tickers
            new_articles = list(db.stock_news.find(query).sort("published_utc", -1).limit(limit))
            
            if new_articles:
                # Update the last timestamp
                last_timestamp = new_articles[0]["published_utc"]
                
                # Format news articles
                formatted_articles = [format_news(a, ticker_list) for a in new_articles]
                
                # Send the new articles to the client
                await websocket.send_text(json.dumps(formatted_articles))
            else:
                # If no new articles, send an empty list
                await websocket.send_text(json.dumps([]))
            
            # Wait for a message from the client (you can adjust the logic here)
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        print(f"Client disconnected from multi-ticker news feed")
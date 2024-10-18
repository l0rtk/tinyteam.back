from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ..database import get_db
import json
from datetime import datetime, timezone
from typing import Optional

router = APIRouter()

def format_transaction(transaction):
    """Helper function to format a single transaction"""
    formatted = dict(transaction)
    formatted['_id'] = str(formatted['_id'])
    formatted['timestamp'] = formatted['timestamp'].isoformat()
    return formatted

@router.websocket("/ws/big_transactions")
async def websocket_endpoint(websocket: WebSocket, source: Optional[str] = Query(None)):
    """
    WebSocket endpoint for receiving big transactions.
    
    This endpoint allows clients to connect via WebSocket and receive updates on big transactions.
    The server will send only new transactions since the last message.
    
    To use this endpoint:
    1. Connect to ws://your-server-address/ws/big_transactions
    2. Send any message to request an update
    3. Receive JSON data containing the latest big transactions
    
    Optional query parameter:
    - source: Filter transactions by source (e.g., "kucoin")
    
    Note: This endpoint is not testable via Swagger UI. Use a WebSocket client to interact with it.
    """
    await websocket.accept()
    db = get_db()
    last_timestamp = datetime.min.replace(tzinfo=timezone.utc)
    try:
        while True:
            # Prepare the query
            query = {"timestamp": {"$gt": last_timestamp}}
            if source:
                query["source"] = source

            # Fetch new big transactions from the database
            big_transactions = list(db.big_transactions.find(query).sort("timestamp", -1).limit(100))
            
            if big_transactions:
                # Update the last timestamp
                last_timestamp = big_transactions[0]["timestamp"]
                
                # Format transactions
                formatted_transactions = [format_transaction(t) for t in big_transactions]
                
                # Send the new transactions to the client
                await websocket.send_text(json.dumps(formatted_transactions))
            else:
                # If no new transactions, send an empty list
                await websocket.send_text(json.dumps([]))
            
            # Wait for a message from the client (you can adjust the logic here)
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        print("Client disconnected")

@router.websocket("/ws/big_transactions/{pair}")
async def websocket_pair_endpoint(websocket: WebSocket, pair: str, source: Optional[str] = Query(None)):
    """
    WebSocket endpoint for receiving big transactions for a specific currency.
    
    This endpoint allows clients to connect via WebSocket and receive updates on big transactions
    where the specified currency is either the base currency or the quote currency.
    The server will send only new transactions since the last message.
    
    To use this endpoint:
    1. Connect to ws://your-server-address/ws/big_transactions/{pair} (e.g., /ws/big_transactions/BTC)
    2. Send any message to request an update
    3. Receive JSON data containing the latest big transactions involving the specified currency
    
    Optional query parameter:
    - source: Filter transactions by source (e.g., "kucoin")
    
    Note: This endpoint is not testable via Swagger UI. Use a WebSocket client to interact with it.
    """
    await websocket.accept()
    db = get_db()
    last_timestamp = datetime.min.replace(tzinfo=timezone.utc)
    
    try:
        while True:
            # Prepare the query
            query = {
                "timestamp": {"$gt": last_timestamp},
                "$or": [
                    {"baseCurrency": pair.upper()},
                    {"quoteCurrency": pair.upper()}
                ]
            }
            if source:
                query["source"] = source

            # Fetch new big transactions from the database for the specific currency
            big_transactions = list(db.big_transactions.find(query).sort("timestamp", -1).limit(100))
            
            if big_transactions:
                # Update the last timestamp
                last_timestamp = big_transactions[0]["timestamp"]
                
                # Format transactions
                formatted_transactions = [format_transaction(t) for t in big_transactions]
                
                # Send the new transactions to the client
                await websocket.send_text(json.dumps(formatted_transactions))
            else:
                # If no new transactions, send an empty list
                await websocket.send_text(json.dumps([]))
            
            # Wait for a message from the client (you can adjust the logic here)
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        print(f"Client disconnected from {pair} big transactions feed")
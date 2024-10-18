from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..database import get_db
import json
from datetime import datetime, timezone
from typing import List, Dict


router = APIRouter()


def convert_object_id(item):
    item['_id'] = str(item['_id'])
    return item

@router.get("/data", response_model=List[Dict])
async def get_all_cryptos():
    db = get_db()
    collection = db["coingecko_data"]
    cryptos = list(collection.find())
    
    # Convert ObjectId to string for each document
    cryptos = [convert_object_id(crypto) for crypto in cryptos]
    
    return cryptos
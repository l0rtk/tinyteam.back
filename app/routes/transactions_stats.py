from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from motor.motor_asyncio import AsyncIOMotorClient
import json
from datetime import datetime, timezone, timedelta
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os 
import asyncio

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client.bitpulse_v2
collection = db.transactions_stats_second

DEFAULT_INTERVAL_SECONDS = 1

async def get_transaction_stats(symbol: str, last_timestamp: datetime, interval_seconds: int, source: Optional[str] = None):
    match_stage = {
        '$match': {
            '$or': [
                {'baseCurrency': symbol},
                {'quoteCurrency': symbol}
            ],
            'timestamp': {'$gt': last_timestamp},
        }
    }
    
    if source:
        match_stage['$match']['source'] = source
    
    group_stage = {
        '$group': {
            '_id': {
                '$toDate': {
                    '$subtract': [
                        {'$toLong': '$timestamp'},
                        {'$mod': [{'$toLong': '$timestamp'}, interval_seconds * 1000]}
                    ]
                }
            },
            'symbol': {'$first': '$symbol'},
            'baseCurrency': {'$first': '$baseCurrency'},
            'quoteCurrency': {'$first': '$quoteCurrency'},
            'buy_count': {'$sum': '$buy_count'},
            'buy_total_quantity': {'$sum': '$buy_total_quantity'},
            'buy_total_value': {'$sum': '$buy_total_value'},
            'buy_min_price': {'$min': '$buy_min_price'},
            'buy_max_price': {'$max': '$buy_max_price'},
            'sell_count': {'$sum': '$sell_count'},
            'sell_total_quantity': {'$sum': '$sell_total_quantity'},
            'sell_total_value': {'$sum': '$sell_total_value'},
            'sell_min_price': {'$min': '$sell_min_price'},
            'sell_max_price': {'$max': '$sell_max_price'}
        }
    }
    
    project_stage = {
        '$project': {
            '_id': 0,
            'timestamp': '$_id',
            'symbol': 1,
            'baseCurrency': 1,
            'quoteCurrency': 1,
            'buy_count': 1,
            'buy_total_quantity': 1,
            'buy_total_value': 1,
            'buy_min_price': 1,
            'buy_max_price': 1,
            'buy_avg_price': {
                '$cond': [
                    {'$eq': ['$buy_total_quantity', 0]},
                    0,
                    {'$divide': ['$buy_total_value', '$buy_total_quantity']}
                ]
            },
            'sell_count': 1,
            'sell_total_quantity': 1,
            'sell_total_value': 1,
            'sell_min_price': 1,
            'sell_max_price': 1,
            'sell_avg_price': {
                '$cond': [
                    {'$eq': ['$sell_total_quantity', 0]},
                    0,
                    {'$divide': ['$sell_total_value', '$sell_total_quantity']}
                ]
            },
            'avg_price': {
                '$cond': [
                    {'$eq': [{'$add': ['$buy_total_quantity', '$sell_total_quantity']}, 0]},
                    0,
                    {'$divide': 
                        [{'$add': ['$buy_total_value', '$sell_total_value']}, 
                         {'$add': ['$buy_total_quantity', '$sell_total_quantity']}]
                    }
                ]
            }
        }
    }
    
    sort_stage = {'$sort': {'timestamp': 1}}
    
    pipeline = [match_stage, group_stage, project_stage, sort_stage]
    
    return await collection.aggregate(pipeline).to_list(length=None)

def format_transaction(transaction, last_price):
    formatted = {
        'timestamp': transaction['timestamp'].isoformat(),
        'symbol': transaction['symbol'],
        'baseCurrency': transaction['baseCurrency'],
        'quoteCurrency': transaction['quoteCurrency'],
        'buy_count': transaction.get('buy_count', 0),
        'buy_total_quantity': transaction.get('buy_total_quantity', 0),
        'buy_total_value': transaction.get('buy_total_value', 0),
        'buy_min_price': transaction.get('buy_min_price', 0),
        'buy_max_price': transaction.get('buy_max_price', 0),
        'buy_avg_price': transaction.get('buy_avg_price', 0),
        'sell_count': transaction.get('sell_count', 0),
        'sell_total_quantity': transaction.get('sell_total_quantity', 0),
        'sell_total_value': transaction.get('sell_total_value', 0),
        'sell_min_price': transaction.get('sell_min_price', 0),
        'sell_max_price': transaction.get('sell_max_price', 0),
        'sell_avg_price': transaction.get('sell_avg_price', 0),
        'avg_price': transaction.get('avg_price', 0)
    }
    
    if formatted['buy_count'] > 0:
        last_price = formatted['buy_avg_price']
    elif formatted['sell_count'] > 0:
        last_price = formatted['sell_avg_price']
    elif formatted['avg_price'] > 0:
        last_price = formatted['avg_price']
    
    return formatted, last_price

def create_empty_transaction(timestamp, symbol, baseCurrency, quoteCurrency, last_price):
    return {
        'timestamp': timestamp.isoformat(),
        'symbol': symbol,
        'baseCurrency': baseCurrency,
        'quoteCurrency': quoteCurrency,
        'buy_count': 0,
        'buy_total_quantity': 0,
        'buy_total_value': 0,
        'buy_min_price': last_price,
        'buy_max_price': last_price,
        'buy_avg_price': last_price,
        'sell_count': 0,
        'sell_total_quantity': 0,
        'sell_total_value': 0,
        'sell_min_price': last_price,
        'sell_max_price': last_price,
        'sell_avg_price': last_price,
        'avg_price': last_price
    }

@router.websocket("/ws/transaction_stats/{symbol}/{interval_seconds}")
async def websocket_endpoint_with_interval(
    websocket: WebSocket,
    symbol: str,
    interval_seconds: int,
    source: Optional[str] = Query(None)
):
    await websocket.accept()
    logger.info(f"WebSocket connection established for symbol: {symbol}, interval: {interval_seconds} seconds, source: {source or 'all'}")

    if interval_seconds not in [1, 10, 30, 60]:
        await websocket.send_text(json.dumps({"error": "Invalid interval. Must be 1, 10, 30, or 60 seconds."}))
        await websocket.close()
        return

    interval = timedelta(seconds=interval_seconds)

    if interval_seconds == 1:
        last_timestamp = datetime.now(timezone.utc) - timedelta(minutes=3)
    elif interval_seconds == 10:
        last_timestamp = datetime.now(timezone.utc) - timedelta(minutes=10)
    elif interval_seconds == 30:
        last_timestamp = datetime.now(timezone.utc) - timedelta(minutes=30)
    elif interval_seconds == 60:
        last_timestamp = datetime.now(timezone.utc) - timedelta(minutes=60)
    
    last_price = None

    try:
        while True:
            try:
                current_time = datetime.now(timezone.utc)

                # Fetch transaction stats since the last timestamp
                transaction_stats = await get_transaction_stats(symbol, last_timestamp, interval_seconds, source)

                if transaction_stats:
                    # Get the first and last transaction timestamps
                    start_time = transaction_stats[0]['timestamp']
                    end_time = transaction_stats[-1]['timestamp']

                    # Create a list to hold all intervals, including empty ones
                    all_intervals = []
                    current_interval = start_time.replace(microsecond=0)

                    while current_interval <= end_time:
                        matching_transaction = next((t for t in transaction_stats if t['timestamp'].replace(microsecond=0) == current_interval), None)

                        if matching_transaction:
                            formatted_transaction, last_price = format_transaction(matching_transaction, last_price)
                            all_intervals.append(formatted_transaction)
                        else:
                            all_intervals.append(create_empty_transaction(current_interval, symbol, transaction_stats[0]['baseCurrency'], transaction_stats[0]['quoteCurrency'], last_price))

                        current_interval += interval

                    logger.debug(f"Sending stats for {symbol} (source: {source or 'all'}): {len(all_intervals)} entries (including empty intervals)")
                    await websocket.send_text(json.dumps(all_intervals))
                    # Update the last timestamp to the most recent stat
                    last_timestamp = end_time
                else:
                    logger.debug(f"No new stats found for {symbol} (source: {source or 'all'}), sending empty list")
                    await websocket.send_text(json.dumps([]))

                # Wait for a message from the client with a timeout
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=60)  # 60 second timeout
                except asyncio.TimeoutError:
                    # If no message received, send a ping to keep the connection alive
                    await websocket.send_text(json.dumps({"type": "ping"}))

            except WebSocketDisconnect:
                logger.info(f"Client disconnected from {symbol} transaction stats WebSocket (source: {source or 'all'})")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket loop for {symbol} (source: {source or 'all'}): {str(e)}")
                try:
                    await websocket.send_text(json.dumps({"error": "Internal server error"}))
                except:
                    logger.error("Failed to send error message, connection might be closed")
                break

    finally:
        logger.info(f"WebSocket connection closed for symbol: {symbol} (source: {source or 'all'})")
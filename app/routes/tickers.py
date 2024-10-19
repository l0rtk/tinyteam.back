from fastapi import APIRouter, HTTPException
from ..database import get_db
from typing import Optional
from pymongo import MongoClient
from bson import json_util
import json
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter()

# MongoDB connection details
MONGODB_URI = os.getenv("MONGO_URI") 
DB_NAME = "tinyteam"
COLLECTION_NAME = "stock_details"

# Initialize MongoDB client
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

@router.get("/stock_details/{ticker}")
async def get_stock_details(ticker: str):
    """
    Endpoint to get detailed information about a specific stock from MongoDB.

    This endpoint fetches comprehensive data about a given stock ticker,
    including company information, financials, and market data.

    Path parameters:
    - ticker: The stock ticker symbol (e.g., AAPL for Apple Inc.)

    Returns a dictionary containing detailed stock information.
    """
    # Query MongoDB for the stock details
    stock_info = collection.find_one({"ticker": ticker})

    if not stock_info:
        raise HTTPException(status_code=404, detail=f"Stock data for ticker {ticker} not found")

    # Remove the MongoDB-specific _id field and convert to JSON
    stock_info.pop('_id', None)
    
    # Format the response to match the desired structure
    formatted_response = {
        "results": {
            "active": stock_info.get("active"),
            "address": stock_info.get("address", {}),
            "branding": stock_info.get("branding", {}),
            "cik": stock_info.get("cik"),
            "composite_figi": stock_info.get("composite_figi"),
            "currency_name": stock_info.get("currency_name"),
            "description": stock_info.get("description"),
            "homepage_url": stock_info.get("homepage_url"),
            "list_date": stock_info.get("list_date"),
            "locale": stock_info.get("locale"),
            "market": stock_info.get("market"),
            "market_cap": stock_info.get("market_cap"),
            "name": stock_info.get("name"),
            "phone_number": stock_info.get("phone_number"),
            "primary_exchange": stock_info.get("primary_exchange"),
            "round_lot": stock_info.get("round_lot"),
            "share_class_figi": stock_info.get("share_class_figi"),
            "share_class_shares_outstanding": stock_info.get("share_class_shares_outstanding"),
            "sic_code": stock_info.get("sic_code"),
            "sic_description": stock_info.get("sic_description"),
            "ticker": stock_info.get("ticker"),
            "ticker_root": stock_info.get("ticker_root"),
            "total_employees": stock_info.get("total_employees"),
            "type": stock_info.get("type"),
            "weighted_shares_outstanding": stock_info.get("weighted_shares_outstanding"),
            "updated_at": stock_info.get("updated_at")
        }
    }

    return formatted_response
from fastapi import APIRouter, HTTPException
from ..database import get_db
from typing import Optional
import httpx

router = APIRouter()

# You would typically store this in an environment variable
API_KEY = "RMpxIDplF6M4YdH9M1xNIYnxsPLCJwGW"
BASE_URL = "https://api.polygon.io/v3/reference/tickers"

@router.get("/stock_details/{ticker}")
async def get_stock_details(ticker: str):
    """
    Endpoint to get detailed information about a specific stock.

    This endpoint fetches comprehensive data about a given stock ticker,
    including company information, financials, and market data.

    Path parameters:
    - ticker: The stock ticker symbol (e.g., AAPL for Apple Inc.)

    Returns a dictionary containing detailed stock information.
    """
    # Construct the URL for the API request
    url = f"{BASE_URL}/{ticker}?apiKey={API_KEY}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch stock data")

        data = response.json()

        # Extract the relevant information from the API response
        stock_info = data.get("results", {})

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
                "weighted_shares_outstanding": stock_info.get("weighted_shares_outstanding")
            }
        }

        return formatted_response
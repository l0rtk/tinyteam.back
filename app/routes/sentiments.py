from fastapi import APIRouter, HTTPException, Query
from ..database import get_db
from datetime import datetime, timedelta
from pymongo import DESCENDING
from typing import List, Optional

router = APIRouter()

@router.get("/sentiment_aggregation")
async def get_sentiment_aggregation(
    keywords: str,
    aggregation_type: str = Query(..., description="Type of aggregation: 'hourly' or 'minutes'"),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    subreddit: Optional[str] = None
):
    """
    Endpoint to get aggregated sentiment data for specified keywords.

    This endpoint provides a summary of positive, negative, and neutral posts
    for each time unit (hour or minute) within the specified time range.

    Query parameters:
    - keywords: Comma-separated list of keywords to track (required)
    - aggregation_type: Type of aggregation, either 'hourly' or 'minutes' (required)
    - start_time: Start of the time range (optional, defaults to 24 hours ago for hourly, 1 hour ago for minutes)
    - end_time: End of the time range (optional, defaults to current time)
    - subreddit: Filter posts by subreddit (optional)

    Returns a list of aggregations, each containing:
    - time_unit: The hour or minute of aggregation
    - positives: Count of positive sentiment posts
    - negatives: Count of negative sentiment posts
    - neutrals: Count of neutral sentiment posts
    """
    db = get_db()

    # Validate aggregation_type
    if aggregation_type not in ['hourly', 'minutes']:
        raise HTTPException(status_code=400, detail="Invalid aggregation_type. Must be 'hourly' or 'minutes'.")

    # Process keywords
    keyword_list = [k.strip().lower() for k in keywords.split(',')]

    # Set default time range if not provided
    if not start_time:
        start_time = datetime.utcnow() - timedelta(hours=24 if aggregation_type == 'hourly' else 1)
    if not end_time:
        end_time = datetime.utcnow()

    # Prepare the query
    query = {
        "keyword": {"$in": keyword_list},
        "created_utc": {"$gte": start_time.timestamp(), "$lte": end_time.timestamp()}
    }
    if subreddit:
        query["subreddit"] = subreddit

    # Set time format based on aggregation type
    time_format = "%Y-%m-%d %H:00" if aggregation_type == 'hourly' else "%Y-%m-%d %H:%M"

    # Aggregation pipeline
    pipeline = [
        {"$match": query},
        {"$project": {
            "created_time": {
                "$dateToString": {
                    "format": time_format,
                    "date": {"$toDate": {"$multiply": ["$created_utc", 1000]}}
                }
            },
            "sentiment_label": 1
        }},
        {"$group": {
            "_id": "$created_time",
            "positives": {
                "$sum": {"$cond": [{"$eq": ["$sentiment_label", "positive"]}, 1, 0]}
            },
            "negatives": {
                "$sum": {"$cond": [{"$eq": ["$sentiment_label", "negative"]}, 1, 0]}
            },
            "neutrals": {
                "$sum": {"$cond": [{"$eq": ["$sentiment_label", "neutral"]}, 1, 0]}
            }
        }},
        {"$sort": {"_id": 1}}
    ]

    results = list(db.reddit.aggregate(pipeline))

    # Format the final output
    formatted_output = [
        {
            "time_unit": result["_id"],
            "positives": result["positives"],
            "negatives": result["negatives"],
            "neutrals": result["neutrals"]
        }
        for result in results
    ]

    return formatted_output
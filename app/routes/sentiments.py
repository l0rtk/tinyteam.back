from fastapi import APIRouter, HTTPException, Query
from ..database import get_db
from datetime import datetime, timedelta
from pymongo import DESCENDING
from typing import List, Optional

router = APIRouter()

def generate_time_series(start_time: datetime, end_time: datetime, aggregation_type: str) -> List[str]:
    """Generate a complete time series between start_time and end_time."""
    time_format = "%Y-%m-%d %H:00" if aggregation_type == 'hourly' else "%Y-%m-%d %H:%M"
    delta = timedelta(hours=1) if aggregation_type == 'hourly' else timedelta(minutes=1)
    time_series = []
    current_time = start_time
    while current_time <= end_time:
        time_series.append(current_time.strftime(time_format))
        current_time += delta
    return time_series

def fill_missing_data(data: List[dict], time_series: List[str]) -> List[dict]:
    """Fill in missing time units with zero counts."""
    data_dict = {item['time_unit']: item for item in data}
    filled_data = []
    for time_unit in time_series:
        if time_unit in data_dict:
            filled_data.append(data_dict[time_unit])
        else:
            filled_data.append({
                'time_unit': time_unit,
                'positives': 0,
                'negatives': 0,
                'neutrals': 0
            })
    return filled_data

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

    # Format the initial output
    formatted_output = [
        {
            "time_unit": result["_id"],
            "positives": result["positives"],
            "negatives": result["negatives"],
            "neutrals": result["neutrals"]
        }
        for result in results
    ]

    # Generate complete time series
    time_series = generate_time_series(start_time, end_time, aggregation_type)

    # Fill in missing data with zeros
    filled_output = fill_missing_data(formatted_output, time_series)

    return filled_output
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, user, big_transactions, transactions_stats, cryptos 
from app.database import init_db
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize database
init_db(os.getenv("MONGO_URI"), os.getenv("MONGO_DB"))

# Include routers
app.include_router(auth.router, prefix="/jwt", tags=["authentication"])
app.include_router(user.router, prefix="/auth", tags=["user"])
app.include_router(big_transactions.router, prefix="/whales",tags=["websocket"])
app.include_router(transactions_stats.router, prefix="/stats",tags=["websocket"])
app.include_router(cryptos.router, prefix="/cryptos",tags=["cryptos"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
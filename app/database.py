from pymongo import MongoClient


def init_db(URI, db_name):
    global client, db
    client = MongoClient(URI)
    db = client[db_name]

def get_db():
    return db
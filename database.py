from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

class MongoDBClient:
    def __init__(self):
        self.mongo_uri = os.getenv("MONGODB_URI")
        if not self.mongo_uri:
            raise ValueError("MONGODB_URI environment variable not set")

        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            self.client.server_info()  # Force connection to check for issues
            self.db = self.client.get_default_database()
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            raise

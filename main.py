from fastapi import FastAPI, HTTPException, Body
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from dotenv import load_dotenv
import os
import logging
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

class QueryItem(BaseModel):
    question: str

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class DBConnection:
    client: AsyncIOMotorClient = None

@app.on_event("startup")
async def startup_db_client():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
    print(mongodb_url)
    DBConnection.client = AsyncIOMotorClient(mongodb_url)
    logger.info("MongoDB connected")

@app.on_event("shutdown")
async def shutdown_db_client():
    DBConnection.client.close()
    logger.info("MongoDB connection closed")

def custom_jsonable_encoder(obj, **kwargs):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, list):
        return [custom_jsonable_encoder(item, **kwargs) for item in obj]
    if isinstance(obj, dict):
        return {key: custom_jsonable_encoder(value, **kwargs) 
                for key, value in obj.items()}
    return jsonable_encoder(obj, **kwargs)

# pass collection name (project name)
# sammple body {
#    "question": "What is the current use of artificial intelligence in software development?"
#}

@app.post("/{collection_name}") 
async def fetch_documents_from_code_async(collection_name: str, query_item: QueryItem = Body(...)):
    db = DBConnection.client['code_sync']
    
    cursor = db[collection_name].find()  
    documents = await cursor.to_list(length=100) 
    
    if not documents:
        raise HTTPException(status_code=404, detail="Documents not found")
    
    querydb = DBConnection.client['langchain_db']['query']
    # save the query to the database
    query = query_item.dict()
    query_id = await querydb.insert_one(query)

    # print the query id
    print(query_id.inserted_id)
    
    encodable_docs = custom_jsonable_encoder(documents)
    return encodable_docs


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
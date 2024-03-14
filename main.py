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

def send_to_sqs(data, queue_name, collection_name):
    import boto3
    import json

    # Create SQS client
    sqs = boto3.client('sqs')

    queue_url = os.getenv("SQS_QUEUE_URL")

    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(data),
        MessageAttributes={
            'QueueName': {
                'DataType': 'String',
                'StringValue': queue_name
            },
            'CollectionName': {
                'DataType': 'String',
                'StringValue': collection_name
            },
            
        }
    )



# pass collection name (project name)
# sammple body {
#    "question": "What is the current use of artificial intelligence in software development?"
#}
@app.post("/debugger/{collection_name}") 
async def fetch_documents_from_code_async(collection_name: str, query_item: QueryItem = Body(...)):
    db = DBConnection.client['code_sync']
    
    cursor = db[collection_name].find()  
    documents = await cursor.to_list(length=100) 
    
    if not documents:
        raise HTTPException(status_code=404, detail="Documents not found")
    
    querydb = DBConnection.client['langchain_db']['debugger_query']
    # save the query to the database
    query = query_item.dict()
    query_id = await querydb.insert_one(query)

    # print the query id
    print(query_id.inserted_id)
    
    encodable_docs = custom_jsonable_encoder(documents)
    return encodable_docs

@app.post("/optimizer/{collection_name}")
async def fetch_documents_from_code_async(collection_name: str, query_item: QueryItem = Body(...)):
    db = DBConnection.client['code_sync']
    
    cursor = db[collection_name].find()  
    documents = await cursor.to_list(length=100) 
    
    if not documents:
        raise HTTPException(status_code=404, detail="Documents not found")
    
    querydb = DBConnection.client['langchain_db']['optimizer_query']
    # save the query to the database
    query = query_item.dict()
    query_id = await querydb.insert_one(query)

    # print the query id
    print(query_id.inserted_id)
    
    encodable_docs = custom_jsonable_encoder(documents)
    return encodable_docs

@app.get("/documentation/{collection_name}")
async def fetch_documents_from_code(collection_name: str):
    db = DBConnection.client['code_sync']
    
    cursor = db[collection_name].find()  
    documents = await cursor.to_list(length=100) 
    
    if not documents:
        raise HTTPException(status_code=404, detail="Documents not found")
    
    encodable_docs = custom_jsonable_encoder(documents)

    # send it to AWS SQS
    await send_to_sqs(encodable_docs, "documentation", collection_name)

    # save with empty documentations
    db = DBConnection.client['langchain_db']['documentation']
    query = {"project_name": collection_name, "documentations": []}
    
    # save the query to the database
    query_id = await db.insert_one(query)

    response = {"message": "your document is being processed and will be available soon"}

    return response

@app.get("/projects")
async def fetch_projects():
    db = DBConnection.client['code_sync']
    projects = await db.list_collection_names()

    # format the response properly
    projects = {"projects": projects}
    return projects

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
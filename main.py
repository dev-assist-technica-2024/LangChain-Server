from fastapi import FastAPI, HTTPException, Body
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from dotenv import load_dotenv
import os
import logging
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import boto3
import json
import asyncio
# from openai import OpenAI

from controller.debugger import Debugger
from controller.security import Security


class QueryItem(BaseModel):
    question: str


load_dotenv()
app = FastAPI()

logger = logging.getLogger(__name__)

queue_url = os.getenv("SQS_QUEUE_URL")
mongodb_url = os.getenv("MONGODB_URL")
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_default_region = os.getenv("AWS_DEFAULT_REGION")


class DBConnection:
    client: AsyncIOMotorClient = None


async def poll_sqs_messages():
    sqs = boto3.client('sqs',
                       aws_access_key_id=aws_access_key_id,
                       aws_secret_access_key=aws_secret_access_key,
                       region_name=aws_default_region)

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                AttributeNames=['All'],
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20
            )

            if 'Messages' in response:
                for message in response['Messages']:
                    print("Message received:", message['Body'])

                    message_body = json.loads(message['Body'])
                    project_name = message_body.get("project_name", "")

                    print(project_name)

                    if message_body.get("task") == "fetch_documentation":
                        print("Fetching documentation...")
                        
                    elif message_body.get("task") == "fetch_steps_to_deploy":
                        print("Fetching steps to deploy...")
                        
                    elif message_body.get("task") == "security":
                        print("Calling for security issues...")
                        await Security.call_assistant_with_markdown(project_name)
                        sqs.delete_message(
                            QueueUrl=queue_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                    
                    sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    print("Message deleted:", message['Body'])
        except Exception as e:
            logger.error(f"Error polling SQS: {e}")

        await asyncio.sleep(1)


@app.on_event("startup")
async def startup_db_client():
    DBConnection.client = AsyncIOMotorClient(mongodb_url)
    logger.info("MongoDB connected")
    # delete the previous messages from the queue
    # TODO: remove this line in production
    sqs = boto3.client('sqs',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_default_region)
    
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=['All'],
        MaxNumberOfMessages=10,
        WaitTimeSeconds=20  
    )

    if 'Messages' in response:
        for message in response['Messages']:
            sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=message['ReceiptHandle']
            )
            print("Message deleted:", message['Body'])

    asyncio.create_task(poll_sqs_messages())


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

async def vulnerable_code(collection_name: str):
    db = DBConnection.client['code_sync']

    cursor = db[collection_name].find()
    documents = await cursor.to_list(length=100)

    if not documents:
        raise HTTPException(status_code=404, detail="Documents not found")

    querydb = DBConnection.client['langchain_db']['documentation_query']
    
    query = {
        "project_name": collection_name,
        "status": "pending",
        "result": None,
        "thread_id": "",
    }

    # Save the updated query to the database
    query_id = await querydb.insert_one(query)

    # Print the query id
    print(query_id.inserted_id)

    encodable_docs = custom_jsonable_encoder(documents)

    print("[]")
    
    return encodable_docs


def send_to_sqs(queue_name, collection_name, task):
    try:
        sqs = boto3.client(
            'sqs',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_default_region
        )

        message_body = json.dumps({
            "project_name": collection_name,
            "task": task
        })

        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body,
            MessageAttributes={
                'QueueName': {
                    'DataType': 'String',
                    'StringValue': queue_name
                },
            }
        )
        print(f"Message sent to SQS. Message ID: {response['MessageId']}")
    except Exception as e:
        print(f"Failed to send message to SQS: {str(e)}")


# pass collection name (project name)
# sample body {
#    "question": "What is the current use of artificial intelligence in software development?"
# }

@app.post("/debugger/{collection_name}/initialize_thread")
async def initialize_thread():
    db = DBConnection.client['langchain_db']['debugger_query']
    debugger = Debugger()
    thread_id, assistant_id = debugger.initialize_thread()
    return {"thread_id": thread_id, "assistant_id": assistant_id}


@app.post("/debugger/{collection_name}/{threadID}/{assistantID}")
async def fetch_documents_from_code_async(collection_name: str, threadID: str, assistantID: str, query_item: QueryItem = Body(...)):
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

    completion = await Debugger.generate_debugger_completions(encodable_docs, threadID, assistantID)
    completion_id = await querydb.insert_one(completion)

    print(completion_id, completion)

    return completion


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

@app.post("/security/{collection_name}")
async def fetch_documentation(collection_name: str):
    querydb = DBConnection.client['langchain_db']['security_query']
    # save the query to the database
    query = {
        "project_name": collection_name,
        "status": "pending",
        "result": None,
    }
    query_id = await querydb.insert_one(query)

    send_to_sqs("security", collection_name, "security")

    return {"message": "Security check is being processed and will be available soon"}
    
@app.post("/documentation/{collection_name}")
async def fetch_documents_from_code(collection_name: str):
    # send it to AWS SQS
    send_to_sqs("documentation", collection_name, "fetch_documentation")

    db = DBConnection.client['langchain_db']['documentation']
    query = {"project_name": collection_name, "documentations": []}

    await db.insert_one(query)

    response = {"message": "your document is being processed and will be available soon"}

    return response


@app.get("/projects")
async def fetch_projects():
    db = DBConnection.client['code_sync']
    projects = await db.list_collection_names()

    # format the response properly
    projects = {"projects": projects}
    return projects


@app.get("/steps-to-deploy/{collection_name}")
async def fetch_steps_to_deploy(collection_name: str):
    db = DBConnection.client['langchain_db']['deployment']

    cursor = db[collection_name].find()
    documents = await cursor.to_list(length=100)

    if not documents:
        raise HTTPException(status_code=404, detail="Documents not found")

    encodable_docs = custom_jsonable_encoder(documents)
    return encodable_docs


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

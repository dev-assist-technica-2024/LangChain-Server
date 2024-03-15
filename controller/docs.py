from openai import OpenAI
from motor.motor_asyncio import AsyncIOMotorClient
import os
import time
import logging
import pprint

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

mongodb_url = os.getenv("MONGODB_URL")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_assistant_id = os.getenv("OPENAI_ASSISTANT_ID")

class DBConnection:
    client: AsyncIOMotorClient = None

class Docs:
    async def call_assistant_with_markdown(collection_name):
        DBConnection.client = AsyncIOMotorClient(mongodb_url)
        client = OpenAI(api_key=openai_api_key)
        db = DBConnection.client['code_sync']
        cursor = db[collection_name].find()

        async for document in cursor:
            empty_thread = client.beta.threads.create() 
            thread_id = empty_thread.id  
           
            thread_message = client.beta.threads.messages.create(
            thread_id,
            role="user",
            content=f"Generate docs for this {document}",
            )

            run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=openai_assistant_id
            )

            while True:
                time.sleep(1)
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                if run.status == "completed":
                    break
            
            messages_page = client.beta.threads.messages.list(thread_id)
            messages = messages_page.data
            if messages:
                print(messages[0].content[0].text.value)
            else:
                print("No messages found in the thread.")

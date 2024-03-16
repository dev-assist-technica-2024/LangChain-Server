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
openai_assistant_id = os.getenv("OPENAI_CHATBOT_ASSISTANT_ID")

class DBConnection:
    client: AsyncIOMotorClient = None

import asyncio

class ChatBot:
    async def generate_chatbot_completions(collection_name, query):
        DBConnection.client = AsyncIOMotorClient(mongodb_url)

        querydb = DBConnection.client['langchain_db']['chatbot']
        # find the query in the database
        query = {
            "project_name": collection_name,
        }

        res = await querydb.find_one
        threadID = res.get("thread_id")
        if threadID is not None:
            print(threadID)
        else:
            print("No thread_id found in the document.")
            return None
        client = OpenAI(api_key=openai_api_key)
        run = client.beta.threads.runs.create(
            thread_id=threadID,
            assistant_id=openai_assistant_id,
            instructions=query
        )

        while run.status in ['queued', 'in_progress', 'cancelling']:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=threadID,
                run_id=run.id
            )
        
        if run.status == 'completed':
            messages = client.beta.threads.messages.list(
                thread_id=threadID
            )
            if messages:
                textArr = messages[0].content[0].text.value
                return textArr
            else:
                print("No messages found in the thread.")

        else:
            print("The run did not complete successfully.")
            return None
        
        return None

    async def call_assistant_with_markdown(collection_name):
        DBConnection.client = AsyncIOMotorClient(mongodb_url)
        client = OpenAI(api_key=openai_api_key)
        db = DBConnection.client['code_sync']
        cursor = db[collection_name].find()

        result = []

        querydb = DBConnection.client['langchain_db']['chatbot']
        # find the query in the database
        query = {
            "project_name": collection_name,
        }
        res = await querydb.find_one(query)
        thread_id = res.get("thread_id")
        if thread_id is not None:
            print(thread_id)
        else:
            print("No thread_id found in the document.")

        async for document in cursor:
            print(document) 

            # if thread_id is None:
                # First create an empty thread
            empty_thread = client.beta.threads.create()
            thread_id = empty_thread.id
           
           # Add message to the thread
            client.beta.threads.messages.create(
                thread_id,
                role="user",
                content=f"{document}",
            )

            # Run the thread with your assistant id
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=openai_assistant_id
            )

            timeout = 600  # seconds
            start_time = time.time()
            
            while True:
                await asyncio.sleep(1) 
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                if run.status == "completed" or time.time() - start_time > timeout:
                    break

            # Proceed only if run completed successfully
            if run.status == "completed":
                messages_page = client.beta.threads.messages.list(thread_id)
                messages = messages_page.data
                if messages:
                    textArr = messages[0].content[0].text.value
                    result.append(textArr)
                else:
                    print("No messages found in the thread.")
            else:
                print("The run did not complete successfully.")

        querydb = DBConnection.client['langchain_db']['chatbot']
        # find the query in the database
        query = {
            "project_name": collection_name,
            "status": "pending",
            "result": None,
        }

        # find the query in the database
        query = await querydb.find_one(query)

        # Filter to find the specific document
        filter_query = {
            "project_name": collection_name,
            "status": "pending",
        }

        update_document = {
            "$set": {
                "result": result,
                "status": "completed",
                "thread_id": thread_id
            }
        }

        update_result = await querydb.update_one(filter_query, update_document)

        if update_result.matched_count > 0:
            print(f"Successfully updated document for project '{collection_name}'.")
            if update_result.modified_count > 0:
                print("The document was modified.")
            else:
                print("The document was not modified (the new data might be the same as the old data).")
        else:
            print(f"No document found for project '{collection_name}' with the specified criteria.")

        


        
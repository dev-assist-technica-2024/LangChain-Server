from openai import OpenAI
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from DocumentationGenerator import DocumentationGenerator
import google.generativeai as genai



# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

gemini_api_key = os.getenv("GEMINI_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_assistant_id = os.getenv("OPENAI_SEC_ASSISTANT_ID")
mongodb_url = os.getenv("MONGODB_URL")

class DBConnection:
    client: AsyncIOMotorClient = None


import asyncio

class TestCases:
    async def get_test_cases(collection_name):
        DBConnection.client = AsyncIOMotorClient(mongodb_url)
        client = OpenAI(api_key=openai_api_key)
        db = DBConnection.client['code_sync']
        cursor = db[collection_name].find()

        result = []

        querydb = DBConnection.client['langchain_db']['test_query']
        
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
         
            fileName = document["name"]
            fileName = fileName.replace(".ts", ".js")
            fileContents = document["content"]

            generator = DocumentationGenerator(fileName, fileContents)
            query_output = generator.query(
            """
            (call_expression
                arguments: (arguments (string) (arrow_function))) @function
            """
            )

            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-pro')
            for _, func_or_class in query_output:
                if "function" not in func_or_class: continue
                response = model.generate_content("generate a proper testcase for the following function also the test case code should have the code and the type like integration, unit test for this function \n" + bytes.decode(func_or_class["function"].text, "utf-8"))
                print(response.text)
                result.append({
                    "name": fileName,
                    "content": bytes.decode(func_or_class["function"].text, "utf-8"),
                    "testCase": response.text
                })



        querydb = DBConnection.client['langchain_db']['test_query']
        # find the query in the database
        query = {
            "project_name": collection_name,
        }

        # find the query in the database
        query = await querydb.find_one(query)

        # Filter to find the specific document
        filter_query = {
            "project_name": collection_name,
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

        


        
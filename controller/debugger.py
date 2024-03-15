from openai import OpenAI
from dotenv import load_dotenv
import time
import logging
import os

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

mongodb_url = os.getenv("MONGODB_URL")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_assistant_id = os.getenv("OPENAI_ASSISTANT_ID")


class Debugger:

    def __init__(self):
        self.client = OpenAI()

    async def initialize_thread(self):
        assistant = self.client.beta.assistants.create(
            name="Code Debugger",
            instructions="You are a code debugger. You will be given an entire codebase along with an error stacktrace or "
                         "user query or both. You will have to identify where the error is happening and give the solution."

                         "You will be given the codebase in the format:"

                         "Codebase:"
                         "{File Path}"
                         "//Code Start"
                         "{Code}"
                         "//Code End"

                         "Everything after the Codebase label are the different files with their file path and code. The files "
                         "denoting code will have //Code Start and //Code End to denote the code. There will be configuration "
                         "files there as well and they wont have the code identifiers so you will know which ones are the "
                         "config files."

                         "After this, you will be given an error stacktrace or the user query. It will be in the format:"

                         "User Query:"
                         "{Error}"

                         "In the error field it will either be some sort of query regarding the code or a stacktrace"

                         "Given all this you will figure out where the error is happening, why the error is happening and give "
                         "the solution with code if necessary. Explain in utmost detail. If"
                         "you don't know the answer, say you don't know.",

            tools=[{"type": "code_interpreter"}],
            model="gpt-4-turbo-preview",
        )
        thread = self.client.beta.threads.create()
        return thread.id, assistant.id

    async def generate_debugger_completions(self, documents, threadID, assistantID):
        prompt = ""
        codePrompt = '''
        %s
        //Code Start
        %s
        //Code End
        
        '''
        userQuery = '''
        \nUser Query
        %s
        '''

        for document in documents:
            prompt = prompt + codePrompt % document.name, document.content

        message = self.client.beta.threads.messages.create(
            thread_id=threadID,
            role="user",

            content='''
Codebase:
./main.py
//Code Start
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.document_loaders import WikipediaLoader

# Load Wikipedia page
loader = WikipediaLoader("https://en.wikipedia.org/wiki/Artificial_intelligence")
docs = loader.load()

# Create LLM and chain
llm = OpenAI(temperature=0)  
chain = RetrievalQA.from_llm_and_documents(llm, docs)

# Ask a query 
query = "Summarize the history of artificial intelligence"
result = chain.run(query)
print(result)
//Code End 


User Query:
The program crashes at times and doesnt always generate the summary properly. What wrong with this? Fix this for me
'''
        )

        run = self.client.beta.threads.runs.create(
            thread_id=threadID,
            assistant_id=assistantID,
            instructions=""
        )

        while run.status in ['queued', 'in_progress', 'cancelling']:
            time.sleep(1)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=threadID,
                run_id=run.id
            )

        if run.status == 'completed':
            messages = self.client.beta.threads.messages.list(
                thread_id=threadID
            )
            if messages.data:
                return messages.data[0].content[0].text.value
            else:
                return "No messages found"

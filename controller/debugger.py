from openai import OpenAI
from dotenv import load_dotenv
import time
import os
from fastapi import HTTPException

load_dotenv()


client = OpenAI()
# assistant = client.beta.assistants.create(
#     name="Code Debugger",
#     instructions="You are a code debugger. You will be given an entire codebase along with an error "
#                  "stacktrace or"
#                  "user query or both. You will have to identify where the error is happening and give the "
#                  "solution."
#
#                  "You will be given the codebase in the format:"
#
#                  "Codebase:"
#                  "{File Path}"
#                  "//Code Start"
#                  "{Code}"
#                  "//Code End"
#
#                  "Everything after the Codebase label are the different files with their file path and code. "
#                  "The files denoting code will have //Code Start and //Code End to denote the code. There "
#                  "will be configuration files there as well and they wont have the code identifiers so you "
#                  "will know which ones are the config files."
#
#                  "After this, you will be given an error stacktrace or the user query. It will be in the "
#                  "format:"
#
#                  "User Query:"
#                  "{Error}"
#
#                  "In the error field it will either be some sort of query regarding the code or a stacktrace"
#
#                  "Given all this you will figure out where the error is happening, why the error is happening "
#                  "and give the solution with code if necessary. Explain in utmost detail. If"
#                  "you don't know the answer, say you don't know.",
#
#     tools=[{"type": "code_interpreter"}],
#     model="gpt-4-turbo-preview",
# )

# os.environ["DEBUGGER_ID"] = assistant.id


async def initialize_thread_debugger():
    thread = client.beta.threads.create()
    return thread.id


async def generate_debugger_completions(documents, threadID, query):
    prompt = ""
    codePrompt = "Codebase:\n%s\n//Code Start\n%s\n//Code End\n "
    userQuery = "\nUser Query\n%s\n"

    for document in documents:
        prompt = prompt + codePrompt % (document['name'], document['content'])
    
    prompt + userQuery % query

    message = client.beta.threads.messages.create(
        thread_id=threadID,
        role="user",

        content=prompt
    )

    run = client.beta.threads.runs.create(
        thread_id=threadID,
        assistant_id=os.getenv("DEBUGGER_ID"),
        instructions=""
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
        return messages.data[0].content[0].text.value, run.status

    elif run.status in ['failed', 'expired']:
        return "Run Failed or Expired", run.status

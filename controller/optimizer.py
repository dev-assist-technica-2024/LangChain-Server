from openai import OpenAI
from dotenv import load_dotenv
import time
import os

load_dotenv()

client = OpenAI()
assistant = client.beta.assistants.create(
    name="Code Optimizer",
    instructions="You are a code optimizer. You will be given a codebase that you need to optimize so that it is "
                 "efficient in terms of time and space complexity. It should also be modular and follow the standard "
                 "design"
                 "and security principles. Other than this, The user might have specific requests regarding the "
                 "nature of optimization so that should be given more weight and the entire code should be optimized"
                 "around that."

                 "You will be given the code in the format:"

                 "Codebase:"
                 "{File Path}"
                 "//Code Start"
                 "{Code}"
                 "//Code End"
                 
                 "Everything after the Codebase label are the different files with their file path and code. "
                 "The files denoting code will have //Code Start and //Code End to denote the code. There "
                 "will be configuration files there as well and they wont have the code identifiers so you "
                 "will know which ones are the config files."

                 "After this, you will be given the user query. It will be in the "
                 "format:"

                 "User Query:"
                 "{Request}"

                 "In the request field it will either be some sort of specific request about the optimization"

                 "Given all this you will look at the entire codebase and optimize any code as best as you can "
                 "keeping the user's requirements in mind. You might have to optimize multiple files or one file. It"
                 "depends entirely on the user's request"
                 "Explain in utmost detail every step you took. If you can't optimize, say you don't know",

    tools=[{"type": "code_interpreter"}],
    model="gpt-4-turbo-preview",
)

os.environ["OPTIMIZER_ID"] = assistant.id


async def initialize_thread_optimizer():
    thread = client.beta.threads.create()
    return thread.id


async def generate_optimizer_completions(documents, threadID, query):
    prompt = ""
    codePrompt = '''
        Codebase:
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
        prompt = prompt + codePrompt % (document['name'], document['content'])

    prompt + userQuery % query

    message = client.beta.threads.messages.create(
        thread_id=threadID,
        role="user",
        content=prompt
    )

    run = client.beta.threads.runs.create(
        thread_id=threadID,
        assistant_id=os.getenv("OPTIMIZER_ID"),
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

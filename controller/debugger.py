import os

from langchain_openai import ChatOpenAI
from langchain.tools.tavily_search import TavilySearchResults
from langchain import hub
from langchain.agents import create_openai_tools_agent
from langchain.agents import AgentExecutor, Agent
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain_community.utilities import StackExchangeAPIWrapper
from langchain_core.tools import Tool

os.environ["TAVILY_API_KEY"] = "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"
os.environ["LANGCHAIN_API_KEY"] = "ls__3138e5c5dc3d4cb6bcde0dcb4e3783c0"
os.environ["GOOGLE_API_KEY"] = "AIzaSyAVRdGweFsb2gowJq-mCEFoYrKNyO0Nfi8"
os.environ["GOOGLE_CSE_ID"] = "c340c2229c9fd4a20"

llm = ChatOpenAI(openai_api_key='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',
                 model="gpt-3.5-turbo-0125",
                 temperature=0)
# search = GoogleSearchAPIWrapper()
stackexchange = StackExchangeAPIWrapper()
stackExchangeTool = Tool(
    name="stack_exchange_search",
    description="Search Stack Overflow for recent results.",
    func=stackexchange.run,
)
# googleSearchTool = Tool(
#     name="google_search",
#     description="Search Google for error",
#     func=search.run
# )
# print(tool.run("Hydration Error failed"))
tools = [stackExchangeTool]
prompt = hub.pull("jacklinkrypton/openai-functions-agent")
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

message_history = MongoDBChatMessageHistory(
    session_id="test_session",
    connection_string="mongodb+srv://jacklinkrypton:shabnam@cluster0.aijcia1.mongodb.net/?retryWrites=true&w"
                      "=majority&appName=Cluster0",
    database_name="testdb",
    collection_name="chat_history",
)
agent_with_chat_history = RunnableWithMessageHistory(
    agent_executor,
    lambda session_id: message_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)


def invoke(code, error) -> None:
    agent_with_chat_history.invoke(
        {"input": f"{error}: \n {code}"},
        config={"configurable": {"session_id": "test_session"}},
    )


code_snippet = '''
            from langchain.llms import OpenAI
            from langchain.vectorstores import FAISS
            from langchain.document_loaders import DirectoryLoader
            from langchain.chains.question_answering import VectorDBQA

            # Load your documents
            loader = DirectoryLoader("./data/")
            documents = loader.load()

            # Create a vectorstore
            vectorstore = FAISS.from_documents(documents, OpenAI(temperature=0))

            # Create the QA chain
            qa = VectorDBQA.from_llm_and_vectorstore(OpenAI(temperature=0), vectorstore)

            # Ask a question
            query = "What is the capital of France?"
            result = qa.run(query)
            print(result)
'''
error_message = "Error: AttributeError: 'FAISS' object has no attribute 'from_documents'"

invoke(code_snippet, error_message)

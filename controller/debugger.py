import os

from langchain_openai import ChatOpenAI
# from langchain.tools.tavily_search import TavilySearchResults
from langchain import hub
from langchain.agents import create_openai_tools_agent
from langchain.agents import AgentExecutor
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain_community.utilities import StackExchangeAPIWrapper
from langchain_core.tools import Tool

mongodb_url = os.getenv("MONGODB_URL")

class Debugger:
    llm = ChatOpenAI(openai_api_key=os.getenv("OPENAI_API_KEY"),
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

    def __init__(self, collection_name, query, code):
        self.collection_name = collection_name
        self.query = query
        self.code = code

    def invoke(self) -> None:
        message_history = MongoDBChatMessageHistory(
            session_id=self.collection_name,
            connection_string=mongodb_url,
            database_name="langchain_db",
            collection_name=self.collection_name,
        )
        agent_with_chat_history = RunnableWithMessageHistory(
            Debugger.agent_executor,
            lambda session_id: message_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )
        agent_with_chat_history.invoke(
            {"input": f"{self.query}: \n {self.code}"},
            config={"configurable": {"session_id": f'{self.collection_name}'}},
        )
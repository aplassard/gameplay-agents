import asyncio
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from typing import Any

load_dotenv()

llm = ChatOpenAI(
                model_name="deepseek/deepseek-chat-v3-0324:free",
                openai_api_base="https://openrouter.ai/api/v1",
                openai_api_key=os.environ.get("OPENROUTER_API_KEY")
            )


# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="uvx",
    # Make sure to update to the full absolute path to your math_server.py file
    args=["--from",
        "git+https://github.com/aplassard/bracket-city-mcp",
        "bracket-city-mcp"
    ]
)


def load_prompt(file_path: str = './basic_prompt.md') -> str | None:
    """
    Loads a prompt from a text file.

    Args:
        file_path (str, optional): The path to the prompt file.
                                   Defaults to './basic_prompt.md'.

    Returns:
        str | None: The content of the file as a string if the file is found,
                    otherwise None.
    """
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                prompt_text = f.read()
            return prompt_text
        except IOError as e:
            print(f"Error reading the file '{file_path}': {e}")
            return None
    else:
        print(f"Error: The prompt file '{file_path}' was not found.")
        return None

# Define an asynchronous main function
async def main():
    prompt = load_prompt()
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Get tools
            tools = await load_mcp_tools(session)
            tool = [t for t in tools if t.name == "load_puzzle"][0]
            
            response = await tool.ainvoke(input={"date_str": "2025-06-15"})

            
            checkpointer = InMemorySaver()
            agent = create_react_agent(llm, 
                                       tools
                                    )

            inputs = {"messages": [HumanMessage(content=prompt)]}

            print("--- Streaming Agent Steps ---")
            async for s in agent.astream(inputs, config={"recursion_limit": 100}):
                print(s)
                print("----------------")

# Run the asynchronous main function
if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import logging
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from langchain.globals import set_verbose, set_debug
#set_verbose(True)
#set_debug(True)

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
            logging.error(f"Error reading the file '{file_path}': {e}")
            return None
    else:
        logging.error(f"Error: The prompt file '{file_path}' was not found.")
        return None

# Define an asynchronous main function
async def main():
    # It might be good to configure logging here if this script can be run independently
    # For now, it will rely on the configuration in bracket_city_graph.py if that's imported first,
    # or use Python's default logging if not.
    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    prompt = load_prompt()
    if not prompt:
        logging.error("Failed to load prompt. Exiting.")
        return

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Get tools
            tools = await load_mcp_tools(session)
            # A more robust way to get the tool, handling potential errors
            load_puzzle_tool = next((t for t in tools if t.name == "load_puzzle"), None)
            
            if not load_puzzle_tool:
                logging.error("load_puzzle tool not found. Exiting.")
                return

            # Assuming this response is for loading a puzzle, might want to log it
            # For now, the task didn't specify logging this particular response.
            # response = await load_puzzle_tool.ainvoke(input={"date_str": "2025-06-08"})
            # logging.debug(f"Response from load_puzzle tool: {response}")
            
            checkpointer = InMemorySaver()
            agent = create_react_agent(llm, 
                                       tools, # Passing all tools, including load_puzzle
                                       checkpointer=checkpointer,)

            inputs = {"messages": [HumanMessage(content=prompt)]}

            logging.info("Streaming Agent Steps...")
            async for s in agent.astream(inputs, config={"recursion_limit": 200, "configurable": {"thread_id": "1"}}):
                logging.debug(s)

# Run the asynchronous main function
if __name__ == "__main__":
    # Basic logging config for standalone execution of this agent script
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    asyncio.run(main())
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="uvx",
    # Make sure to update to the full absolute path to your math_server.py file
    args=["--from",
        "git+https://github.com/aplassard/bracket-city-mcp",
        "bracket-city-mcp"
    ]
)

# Define an asynchronous main function
async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Get tools
            tools = await load_mcp_tools(session)
            print(f"Tools: {tools}")

            [print(tool.name) for tool in tools]
            
            tool = [t for t in tools if t.name == "load_puzzle"][0]
            print(f"Tool: {tool}")
            response = await tool.ainvoke(input={"date_str": "2025-06-17"})
            print(f"Response: {response}")

# Run the asynchronous main function
if __name__ == "__main__":
    asyncio.run(main())
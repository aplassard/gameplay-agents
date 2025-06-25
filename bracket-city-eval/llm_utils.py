# This file will contain the LLM call logic with retries.
import os
import logging
import time # For exponential backoff, though tenacity handles it internally

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

# Configure logging for this module (optional, but good practice)
logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_llm_with_retry(model_name: str, prompt_message: str) -> str:
    """
    Calls the LLM with the given model name and prompt message.
    Includes retrying with exponential backoff (3 tries, wait 2^x seconds between retries).
    """
    logger.info(f"Attempting to call LLM (model: {model_name})...")
    try:
        llm = ChatOpenAI(
            model_name=model_name,
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        response = llm.invoke([HumanMessage(content=prompt_message)])
        logger.info("LLM call successful.")
        return response.content
    except Exception as e:
        logger.warning(f"LLM call failed. Error: {e}. Retrying if attempts remain...")
        raise # Reraise the exception to trigger tenacity's retry mechanism

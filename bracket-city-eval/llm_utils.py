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

def heal_llm_output(broken_text: str, model_name: str) -> str:
    """
    Takes malformed text and uses an LLM to correct its structure.
    """
    prompt = f"""
Your task is to correct the formatting of the text provided below.The required output format is exactly two lines, as follows:clue_id: <clue id>
answer: <answer text>Review the text and extract the clue_id and the answer.You MUST NOT include any extra text, conversation, explanations, or markdown formatting like ```. Only return the two lines in the specified format.Here is the text to fix:{broken_text}"""

    logger.info(f"Attempting to heal LLM output with model: {model_name}...")
    try:
        healed_text = call_llm_with_retry(model_name, prompt)
        logger.info("LLM healing call successful.")
        return healed_text
    except Exception as e:
        logger.error(f"LLM healing call failed after retries. Error: {e}")
        # Depending on desired behavior, could return original text or raise
        # For now, re-raising the exception to make it visible if healing fails.
        raise

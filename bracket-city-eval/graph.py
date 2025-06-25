from typing_extensions import TypedDict
from bracket_city_mcp.game.game import Game
from bracket_city_mcp.puzzle_loader import load_game_data_by_date

import logging
from langgraph.graph import StateGraph, END
from llm_utils import call_llm_with_retry

import os
import uuid # Added for generating unique filenames
from pathlib import Path # Added for path manipulation


# Ensure the parse-errors directory exists
Path("./parse-errors").mkdir(parents=True, exist_ok=True)

class State(TypedDict):
    game: Game
    llm_message: str | None
    llm_response: str | None
    step_count: int
    max_steps: int
    game_over: bool
    game_won: bool
    model_name: str # Added model_name to state

game_instructions = """
You are an expert at the bracket city game tasked with solving a puzzle that is provided to you. 
Start by reviewing the full text of the puzzle then by reviewing the individual clues that are available.
All clue answers will be a single word.
If you are ever unsure of the clue's answer you can also get the full context of the clue and see if there is a parent clue that may give you more context on the clue you are trying to solve (often clues will be nested i.e. [exercise in a [game played with a cue ball]] if you do not know [game played with a cue ball] you can look at exercise in a to know that the answer to [game played with a cue ball] also should complete the "exercise in a" sentence).
Every incorrect guess hurts your score though, so be careful!"""

conclusion = """Let me know which clue you want to answer and what your guess is. Please only answer one clue. 
Your answer should be structured as
clue_id: [your_clue_id]
answer: [your_answer]
"""

def build_llm_message(game: Game) -> str:
    """
    Build the LLM message based on the current game state.
    Target:
    {game instructions}
    {rendered_game_state}
    {active clues + previous guesses}
    {conclusion structure}
    """
    output = ""
    output += game_instructions + "\n\n"
    output += "The game state is as follows:\n"
    output += game.get_rendered_game_text() + "\n\n"
    output += "The available clues are:\n"
    for clue in game.active_clues:
        output += f"clue_id: {clue}\n"
        output += f"- text: {game.clues.get(clue).get_rendered_text(game)}\n"
        output += f"- previous guesses: {game.clues.get(clue).previous_answers}\n\n"
    output += conclusion + "\n"
    return output

def pre_hook_node(state: State):
    # The full state dump can be very verbose, consider logging specific parts if needed
    # logging.debug(f"Current state: {state}")
    logging.info(f"Steps: {state['step_count']}, Clues Answered: {len(list(filter(lambda x: x.completed, state['game'].clues.values())))}, Total Clues: {len(state['game'].clues)}")
    if state["step_count"] == state["max_steps"]:
        return {"game_over": True, "game_won": False}
    elif state["game"].is_complete:
        return {"game_over": True, "game_won": True}
    else:
        llm_message = build_llm_message(state["game"])
        logging.debug(f"Generated prompt for LLM: {llm_message}")
        return {"llm_message": llm_message, "llm_response": "", "game_over": False, "game_won": False}
    
def call_llm_node(state: State):
    logging.debug(f"Calling LLM with message: {state['llm_message']}")
    # Use the new function from llm_utils
    try:
        response_content = call_llm_with_retry(
            model_name=state["model_name"],
            prompt_message=state["llm_message"]
        )
        logging.debug(f"LLM Response: {response_content}")
        return {"llm_response": response_content}
    except Exception as e:
        # If retries fail, log the error and potentially set an error state or stop the graph.
        # For now, let's log and return an empty response to avoid breaking the graph flow,
        # but this might need more sophisticated error handling based on game requirements.
        logging.error(f"LLM call failed after multiple retries: {e}")
        # Consider how a persistent failure should affect the game state.
        # For example, should it end the game, or skip the LLM turn?
        # Returning None or an empty string for llm_response might cause issues downstream
        # if not handled. For now, let's ensure parse_llm_response can handle it.
        # We could also add an 'error' field to the state.
        return {"llm_response": ""} # Or handle error state appropriately

def _parse_text_to_clue_answer(text_response: str) -> tuple[str | None, str | None]:
    """
    Helper function to parse text into clue_id and answer.
    Returns (None, None) if parsing fails.
    """
    lines = text_response.split("\n")
    clue_id = None
    answer = None
    for line in lines:
        if line.startswith("clue_id:"):
            clue_id = line.split(":", 1)[1].strip() # Use split with maxsplit=1
        elif line.startswith("answer:"):
            answer = line.split(":", 1)[1].strip() # Use split with maxsplit=1

    if clue_id and answer: # Ensure both are found and not empty
        return clue_id, answer
    return None, None

def correct_llm_response(unparseable_text: str, model_name: str) -> str | None:
    """
    Attempts to correct an unparseable LLM response by sending it to another LLM.
    """
    correction_prompt = f"""The following text is an attempted response from an LLM that should conform to the structure:
clue_id: [clue_id_value]
answer: [answer_value]

However, the text is malformed. Please correct it and return ONLY the corrected text in the specified structure. Do not include any preamble or explanation. Also if it is not obvious as to what the correct answer is, don't attempt to come up with an answer.

Malformed text:
---
{unparseable_text}
---
Corrected text:"""

    logging.info(f"Attempting to correct malformed LLM response with model {model_name}.")
    try:
        corrected_text = call_llm_with_retry(
            model_name=model_name,
            prompt_message=correction_prompt
        )
        logging.info(f"Correction attempt response: {corrected_text}")
        return corrected_text
    except Exception as e:
        logging.error(f"LLM call for correction failed: {e}")
        return None

def parse_llm_response(llm_response: str, model_name: str): # Added model_name parameter
    """
    Parse the LLM response to extract the clue ID and answer.
    Attempts correction if initial parsing fails.
    The response should be structured as:
    clue_id: [your_clue_id]
    answer: [your_answer]
    """
    clue_id, answer = _parse_text_to_clue_answer(llm_response)

    if clue_id is not None and answer is not None:
        return clue_id, answer

    # Initial parsing failed, try to correct
    logging.warning(f"Initial parsing failed for response: {llm_response}. Attempting correction.")
    corrected_response_text = correct_llm_response(llm_response, model_name)

    if corrected_response_text:
        clue_id, answer = _parse_text_to_clue_answer(corrected_response_text)
        if clue_id is not None and answer is not None:
            logging.info(f"Successfully parsed after correction. Original: '{llm_response}', Corrected: '{corrected_response_text}'")
            # Optionally, save the corrected response or note that correction was successful.
            # For now, just return the successfully parsed values.
            return clue_id, answer
        else:
            logging.warning(f"Parsing failed even after correction attempt. Corrected text: '{corrected_response_text}'")
    else:
        logging.warning("Correction attempt did not return any text.")

    # All attempts failed, save original error and return None, None
    logging.error(f"Could not parse clue_id or answer from LLM response (even after correction attempt): {llm_response}")
    error_filename = f"./parse-errors/{uuid.uuid4()}.txt"
    with open(error_filename, "w") as f:
        f.write(llm_response) # Save the original erroneous response
    logging.info(f"Saved original unparseable LLM response to {error_filename}")
    return None, None

def answer_clue_node(state: State):
    clue_id, answer = parse_llm_response(state["llm_response"], state["model_name"]) # Pass model_name
    # Log before answering, in case answer_clue raises an error
    logging.debug(f"Attempting to answer clue_id: {clue_id} with answer: {answer}")

    if clue_id is None or answer is None:
        # Error message now includes the fact that the response was saved to a file
        logging.warning(f"Could not parse clue_id or answer from LLM response. Response saved to ./parse-errors/. Skipping answer attempt.")
        # Potentially increment step_count here or handle as an error state depending on desired game logic
        return {"step_count": state["step_count"] + 1, "llm_message": None, "llm_response": None}

    game_instance = state["game"]
    clue_before_answer = game_instance.clues.get(clue_id)

    if not clue_before_answer:
        logging.error(f"Clue with id {clue_id} not found in game state. LLM hallucinated a clue_id.")
        # Potentially increment step_count here or handle as an error state
        return {"step_count": state["step_count"] + 1, "llm_message": None, "llm_response": None}

    game_instance.answer_clue(clue_id, answer)

    clue_after_answer = game_instance.clues.get(clue_id)
    is_correct = clue_after_answer.completed if clue_after_answer else None # Should always exist if no error before

    logging.debug(f"Answered clue_id: {clue_id} with answer: {answer}. Correct: {is_correct}")
    return {"step_count": state["step_count"] + 1,  "llm_message": None, "llm_response": None}

# --- Conditional Edge Logic ---

def should_continue(state: State):
    """Determines whether the game should continue or end."""
    if state["game_over"]:
        return "end"
    else:
        return "call_llm"

# --- Graph Compilation ---

# 1. Initialize the StateGraph
workflow = StateGraph(State)

# 2. Add the nodes
workflow.add_node("pre_hook", pre_hook_node)
workflow.add_node("call_llm", call_llm_node)
workflow.add_node("answer_clue", answer_clue_node)

# 3. Set the entry point
workflow.set_entry_point("pre_hook")

# 4. Add the conditional edge
# After the pre_hook, it will check the `should_continue` function.
# If it returns "end", the graph finishes.
# If it returns "call_llm", it proceeds to that node.
workflow.add_conditional_edges(
    "pre_hook",
    should_continue,
    {
        "end": END,
        "call_llm": "call_llm",
    },
)

# 5. Add the regular edges to form the loop
workflow.add_edge("call_llm", "answer_clue")
workflow.add_edge("answer_clue", "pre_hook")

# 6. Compile the graph
app = workflow.compile()
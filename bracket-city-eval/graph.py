from typing_extensions import TypedDict
from bracket_city_mcp.game.game import Game
from bracket_city_mcp.puzzle_loader import load_game_data_by_date

import logging
from langgraph.graph import StateGraph, END
# Removed ChatOpenAI, HumanMessage, os, load_dotenv as they are now in llm_utils
from .llm_utils import call_llm_with_retry


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

def parse_llm_response(llm_response: str):
    """
    Parse the LLM response to extract the clue ID and answer.
    The response should be structured as:
    clue_id: [your_clue_id]
    answer: [your_answer]
    """
    lines = llm_response.split("\n")
    clue_id = None
    answer = None
    for line in lines:
        if line.startswith("clue_id:"):
            clue_id = line.split(":")[1].strip()
        elif line.startswith("answer:"):
            answer = line.split(":")[1].strip()
    return clue_id, answer

def answer_clue_node(state: State):
    clue_id, answer = parse_llm_response(state["llm_response"])
    # Log before answering, in case answer_clue raises an error
    logging.debug(f"Attempting to answer clue_id: {clue_id} with answer: {answer}")

    if clue_id is None or answer is None:
        logging.warning(f"Could not parse clue_id or answer from LLM response: {state['llm_response']}. Skipping answer attempt.")
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
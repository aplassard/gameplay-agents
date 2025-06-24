from typing_extensions import TypedDict
from bracket_city_mcp.game.game import Game
from bracket_city_mcp.puzzle_loader import load_game_data_by_date

import logging
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

import os
from dotenv import load_dotenv

load_dotenv()

# llm will be initialized dynamically in call_llm_node
# llm = ChatOpenAI(
#                 model_name="openai/gpt-4.1-nano", # This will be dynamic
#                 openai_api_base="https://openrouter.ai/api/v1",
#                 openai_api_key=os.environ.get("OPENROUTER_API_KEY")
#             )

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
    # Initialize LLM dynamically with model_name from state
    llm = ChatOpenAI(
        model_name=state["model_name"],
        openai_api_base="https://openrouter.ai/api/v1", # Assuming this remains constant
        openai_api_key=os.environ.get("OPENROUTER_API_KEY") # Assuming this remains constant
    )
    response = llm.invoke([HumanMessage(state["llm_message"])])
    logging.debug(f"LLM Response: {response.content}")
    return {"llm_response": response.content}

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
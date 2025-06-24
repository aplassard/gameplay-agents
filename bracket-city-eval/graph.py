from typing_extensions import TypedDict
from bracket_city_mcp.game.game import Game
from bracket_city_mcp.puzzle_loader import load_game_data_by_date

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
                model_name="mistralai/mistral-small-3.2-24b-instruct:free",
                openai_api_base="https://openrouter.ai/api/v1",
                openai_api_key=os.environ.get("OPENROUTER_API_KEY")
            )

class State(TypedDict):
    game: Game
    llm_message: str | None
    llm_response: str | None
    step_count: int
    max_steps: int
    game_over: bool
    game_won: bool

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
    print(state)
    print(f"Of the {len(state["game"].clues)} clues, {len(list(filter(lambda x: x.completed, state["game"].clues.values())))} are completed")
    if state["step_count"] == state["max_steps"]:
        return {"game_over": True, "game_won": False}
    elif state["game"].is_complete:
        return {"game_over": True, "game_won": True}
    else:
        llm_message = build_llm_message(state["game"])
        return {"llm_message": llm_message, "llm_response": "", "game_over": False, "game_won": False}
    
def call_llm_node(state: State):
    response = llm.invoke([HumanMessage(state["llm_message"])])
    print(f"LLM Response: {response.content}")
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
    print(f"Answering clue {clue_id} with answer {answer}")
    state["game"].answer_clue(clue_id, answer)
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

if __name__ == "__main__":
    # Load the game data for a specific date
    date_str = "2025-06-07"
    game = Game(load_game_data_by_date(date_str))

    initial_state = {
        "game": game,
        "step_count": 0,
        "max_steps": 50, # Set a limit to prevent infinite loops
    }

    print("Starting Bracket City Solver Graph...")
    # The graph will stream events as it runs
    final_state = app.invoke(initial_state, {"recursion_limit": 1000})

    print("\n--- Graph Finished ---")
    print(f"Game Won: {final_state['game_won']}")
    print(f"Final Score (Steps Taken): {final_state['step_count']}")
    print("Final Game State:")
    print(final_state['game'].get_rendered_game_text())
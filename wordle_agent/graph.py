from typing_extensions import TypedDict
from wordle import wordle
from langgraph.graph import StateGraph, END
import os
import logging
import re
from llmutils.llm_with_retry import call_llm_with_retry
from llmutils.self_healing import heal_llm_output

class State(TypedDict):
    game: wordle.Wordle
    llm_message: str | None
    llm_response: str | None
    llm_responses_history: list[str]
    step_count: int
    max_steps: int
    game_over: bool
    game_won: bool
    model_name: str

def get_prompt_template():
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
    with open(prompt_path, "r") as f:
        return f.read()

def format_history(game: wordle.Wordle):
    history_lines = []
    for guess in game.guesses:
        result_str = "".join(map_color_to_char(color) for color in guess.colors)
        history_lines.append(f"{guess.word} -> {result_str}")
    return "\n".join(history_lines)

def map_color_to_char(color: wordle.LetterColor):
    if color == wordle.LetterColor.GREEN:
        return "G"
    elif color == wordle.LetterColor.YELLOW:
        return "Y"
    else: # LetterColor.GRAY
        return "X"

def pre_hook_node(state: State):
    if len(state["game"].guesses) >= state["game"].turns or (len(state["game"].guesses) > 0 and state["game"].guesses[-1].word == state["game"].word):
        return {"game_over": True, "game_won": len(state["game"].guesses) > 0 and state["game"].guesses[-1].word == state["game"].word}
    
    game_history = format_history(state["game"])
    prompt_template = get_prompt_template()
    llm_message = prompt_template.format(game_history=game_history)
    
    return {
        "llm_message": llm_message,
        "game_over": False,
        "game_won": False,
    }

def call_llm_node(state: State):
    logging.debug(f"Calling LLM with message: {state['llm_message']}")
    try:
        response_content = call_llm_with_retry(
            model_name=state["model_name"],
            prompt_message=state["llm_message"]
        )
        logging.debug(f"LLM Response before healing: {response_content}")
        history = state.get("llm_responses_history", [])
        history.append(response_content)
        return {"llm_responses_history": history, "llm_response": response_content}
    except Exception as e_call:
        logging.error(f"LLM call failed after multiple retries: {e_call}")
        return {"llm_response": "", "llm_responses_history": state.get("llm_responses_history", [])}

def parse_guess(response: str) -> str | None:
    match = re.search(r"guess:\s*(\w+)", response, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return None

def take_turn_node(state: State):
    guess = parse_guess(state["llm_response"])
    if not guess:
        logging.warning(f"Could not parse guess from LLM response: {state['llm_response']}. Attempting to heal.")
        try:
            healed_response = heal_llm_output(
                broken_text=state["llm_response"],
                expected_format="guess: <five letter word>",
                model_name=state["model_name"]
            )
            guess = parse_guess(healed_response)
            if not guess:
                logging.error(f"Failed to heal and parse guess from response: {healed_response}")
                return {"step_count": state["step_count"] + 1}
        except Exception as e_heal:
            logging.error(f"Failed to heal and make a guess: {e_heal}")
            return {"step_count": state["step_count"] + 1}

    try:
        state["game"].guess_word(guess)
        logging.info(f"Guess: {guess} -> {"".join(map_color_to_char(color) for color in state["game"].guesses[-1].colors)}")
        return {"step_count": state["step_count"] + 1}
    except ValueError as e:
        logging.warning(f"Invalid guess: {e}.")
        return {"step_count": state["step_count"] + 1}

    return {
        "llm_message": None,
        "llm_response": None,
    }

def should_continue(state: State):
    if state["game_over"]:
        return "end"
    else:
        return "call_llm"

workflow = StateGraph(State)

workflow.add_node("pre_hook", pre_hook_node)
workflow.add_node("call_llm", call_llm_node)
workflow.add_node("take_turn", take_turn_node)

workflow.set_entry_point("pre_hook")

workflow.add_conditional_edges(
    "pre_hook",
    should_continue,
    {
        "end": END,
        "call_llm": "call_llm",
    },
)

workflow.add_edge("call_llm", "take_turn")
workflow.add_edge("take_turn", "pre_hook")

app = workflow.compile()
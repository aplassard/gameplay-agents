import logging
import uuid
import json
import os
import sys # Add sys import
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) # Add parent dir to path

from bracket_city_mcp.puzzle_loader import load_game_data_by_date
from bracket_city_mcp.game.game import Game
from langchain_community.callbacks import get_openai_callback

from graph import app

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

def main():
    run_id = str(uuid.uuid4())
    # Load the game data for a specific date
    date_str = "2025-06-08"
    game = Game(load_game_data_by_date(date_str))
    logging.info(f"Date selected for puzzle: {date_str}")
    
    initial_state = {
        "game": game,
        "step_count": 0,
        "max_steps": 50, # Set a limit to prevent infinite loops
    }

    with get_openai_callback() as cb:
        logging.info("Starting Bracket City Solver Graph...")
        # The graph will stream events as it runs
        final_state = app.invoke(initial_state, {"recursion_limit": 1000})

        logging.info("Graph Finished.")
        logging.info(f"Game Won: {final_state['game_won']}")
        logging.info(f"Final Score (Steps Taken): {final_state['step_count']}")
        logging.debug(f"Final Game State:\n{final_state['game'].get_rendered_game_text()}")
        logging.debug(f"Token Usage: {cb}")

        result = {
            "game_completed": final_state["game_won"],
            "number_of_steps": final_state["step_count"],
            "puzzle_date": date_str,
            "model_name": "gpt-4o", # Replace with actual model name if available dynamically
            "prompt_tokens": cb.prompt_tokens,
            "prompt_tokens_cached": cb.prompt_tokens_cached,
            "reasoning_token": cb.completion_tokens, # Assuming reasoning_token is completion_tokens based on typical usage
            "completion_tokens": cb.completion_tokens,
            "total_cost": cb.total_cost,
            "run_id": run_id
        }

        results_dir = "bracket-city-eval/results"
        os.makedirs(results_dir, exist_ok=True)

        result_filepath = os.path.join(results_dir, f"{run_id}.json")
        with open(result_filepath, 'w') as f:
            json.dump(result, f, indent=4)

        logging.info(f"Results saved to {result_filepath}")

if __name__ == "__main__":
    main()
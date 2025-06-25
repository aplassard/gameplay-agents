import logging
import argparse # Added import
import uuid
import json
import os
import sys

from bracket_city_mcp.puzzle_loader import load_game_data_by_date
from bracket_city_mcp.game.game import Game
from langchain_community.callbacks import get_openai_callback

from graph import app

# Configure logging
# Logging configuration will be handled after argument parsing

def main():
    parser = argparse.ArgumentParser(description="Run the Bracket City Solver Graph with specified parameters.")
    parser.add_argument("--model-name", type=str, required=True, help="Name of the model to use.")
    parser.add_argument("--date-str", type=str, required=True, help="Date string for the puzzle data (e.g., YYYY-MM-DD).")
    parser.add_argument("--logging-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Logging level (default: INFO).")
    parser.add_argument("--num_steps", type=int, default=50, help="Maximum number of steps for the solver (default: 50).")

    args = parser.parse_args()

    # Configure logging based on parsed argument
    numeric_logging_level = getattr(logging, args.logging_level.upper(), None)
    if not isinstance(numeric_logging_level, int):
        raise ValueError(f"Invalid log level: {args.logging_level}")
    logging.basicConfig(level=numeric_logging_level, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    logging.info(f"Using model: {args.model_name}") # Log the model name

    run_id = str(uuid.uuid4())
    # Load the game data for a specific date
    game = Game(load_game_data_by_date(args.date_str))
    logging.info(f"Date selected for puzzle: {args.date_str}")
    
    initial_state = {
        "game": game,
        "step_count": 0,
        "max_steps": args.num_steps, # Use parsed num_steps
        "model_name": args.model_name, # Pass model_name to the graph
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
            "puzzle_date": args.date_str, # Use args.date_str
            "model_name": args.model_name, # Use args.model_name
            "prompt_tokens": cb.prompt_tokens,
            "prompt_tokens_cached": cb.prompt_tokens_cached,
            "reasoning_token": cb.reasoning_tokens,
            "completion_tokens": cb.completion_tokens,
            "total_cost": cb.total_cost,
            "run_id": run_id
        }

        results_dir = "./results"
        os.makedirs(results_dir, exist_ok=True)

        result_filepath = os.path.join(results_dir, f"{run_id}.json")
        with open(result_filepath, 'w') as f:
            json.dump(result, f, indent=4)

        logging.info(f"Results saved to {result_filepath}")

if __name__ == "__main__":
    main()
import logging
from bracket_city_mcp.puzzle_loader import load_game_data_by_date
from bracket_city_mcp.game.game import Game
from langchain_community.callbacks import get_openai_callback

from graph import app

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

def main():
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

        # The result dictionary is not explicitly printed anymore,
        # its components are logged above or assumed to be used elsewhere.
        # If specific components of 'result' need to be logged, they can be added here.
        # For example:
        # logging.debug(f"Result - Prompt Tokens: {cb.prompt_tokens}, Completion Tokens: {cb.completion_tokens}, Total Cost: {cb.total_cost}")

if __name__ == "__main__":
    main()
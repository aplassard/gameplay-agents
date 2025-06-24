from bracket_city_mcp.puzzle_loader import load_game_data_by_date
from bracket_city_mcp.game.game import Game
from langchain_community.callbacks import get_openai_callback

from graph import app

def main():
    # Load the game data for a specific date
    date_str = "2025-06-08"
    game = Game(load_game_data_by_date(date_str))
    
    initial_state = {
        "game": game,
        "step_count": 0,
        "max_steps": 50, # Set a limit to prevent infinite loops
    }

    with get_openai_callback() as cb:
        print("Starting Bracket City Solver Graph...")
        # The graph will stream events as it runs
        final_state = app.invoke(initial_state, {"recursion_limit": 1000})

        print("\n--- Graph Finished ---")
        print(f"Game Won: {final_state['game_won']}")
        print(f"Final Score (Steps Taken): {final_state['step_count']}")
        print("Final Game State:")
        print(final_state['game'].get_rendered_game_text())

        print("\n--- Token Usage ---")
        print(cb)

        result = {"game_completed": final_state["game_won"], 
                  "number_of_steps": final_state["step_count"], 
                  "puzzle_date": date_str,
                  "prompt_tokens": cb.prompt_tokens,
                  "prompt_tokens_cached": cb.prompt_tokens_cached,
                  "reasoning_token": cb.reasoning_tokens,
                  "completion_tokens": cb.completion_tokens,
                  "total_cost": cb.total_cost
                  }
        print(result)

if __name__ == "__main__":
    main()
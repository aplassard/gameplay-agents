from bracket_city_mcp.puzzle_loader import load_game_data_by_date
from bracket_city_mcp.game.game import Game

#STEPS:
# 1. Load the game
# 2. Create the LLM
# 3. Build the graph for the LLM
# 3a. Render thing we ask llm
# 3b. Conditional logic - if game over (either game complete, or turn limit reached) - end, else send to LLM
# 3c. Call the LLM and ask it what question it wants to answer
# 3d. Try the answer (increment the step count)
# 3e. Return to 3a and loop until game over
# 4. Test

def main():
    # Load the game data for a specific date
    date_str = "2025-06-08"
    game = Game(load_game_data_by_date(date_str))
    
    # Print the loaded game data
    print(game.available_clues())

if __name__ == "__main__":
    main()
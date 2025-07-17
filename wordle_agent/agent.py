from wordle import wordle
from .graph import app, State

class WordleAgent:
    def __init__(self, llm_name, word, turns=6):
        self.llm_name = llm_name
        self.word = word
        self.turns = turns

    def run(self):
        initial_state = State(
            game=wordle.Wordle(self.word, self.turns),
            llm_message=None,
            llm_response=None,
            step_count=0,
            max_steps=self.turns,
            game_over=False,
            game_won=False,
            model_name=self.llm_name,
        )

        final_state = app.invoke(initial_state)

        if final_state["game_won"]:
            print(f"Solved in {final_state['step_count']} turns!")
        else:
            print(f"Failed to solve. The word was {final_state['game'].word}")

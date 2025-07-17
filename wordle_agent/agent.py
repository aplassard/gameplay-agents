from wordle import wordle
from .graph import app, State
import json
import uuid
import os
import time

class WordleAgent:
    def __init__(self, llm_name, word, turns=6, results_dir=None):
        self.llm_name = llm_name
        self.word = word
        self.turns = turns
        self.results_dir = results_dir

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

        start_time = time.time()
        final_state = app.invoke(initial_state, {"recursion_limit": 1000})
        end_time = time.time()
        total_time = end_time - start_time

        if final_state["game_won"]:
            print(f"Solved in {final_state['step_count']} turns!")
        else:
            print(f"Failed to solve. The word was {final_state['game'].word}")

        if self.results_dir:
            self.save_results(final_state, total_time)

    def save_results(self, final_state, total_time):
        os.makedirs(self.results_dir, exist_ok=True)
        game_id = str(uuid.uuid4())
        results = {
            "id": game_id,
            "model": self.llm_name,
            "word": self.word,
            "guesses": [guess.word for guess in final_state["game"].guesses],
            "solved": final_state["game_won"],
            "turns": final_state["step_count"],
            "time": total_time,
        }
        with open(os.path.join(self.results_dir, f"{game_id}.json"), "w") as f:
            json.dump(results, f, indent=4)

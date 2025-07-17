import logging
import argparse
from .agent import WordleAgent

def main():
    parser = argparse.ArgumentParser(description="Play a game of Wordle with an LLM agent.")
    parser.add_argument("--model", type=str, default="openai/gpt-4.1-mini", help="The name of the language model to use.")
    parser.add_argument("--turns", type=int, default=6, help="The number of turns to play.")
    parser.add_argument("--word", type=str, required=True, help="The target word to guess.")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="The logging level to use.")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level), format='%(asctime)s - %(levelname)s - %(message)s')
    agent = WordleAgent(llm_name=args.model, word=args.word, turns=args.turns)
    agent.run()

if __name__ == "__main__":
    main()

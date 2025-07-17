import logging
from .agent import WordleAgent

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # You can change the word and llm_name here
    agent = WordleAgent(llm_name="openai/gpt-4.1-mini", word="apple")
    agent.run()

if __name__ == "__main__":
    main()
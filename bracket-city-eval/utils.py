# This file will contain utility functions for the bracket-city-eval project.
import argparse

def parse_args():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Run the Bracket City Solver Graph with specified parameters.")
    parser.add_argument("--model-name", type=str, required=True, help="Name of the model to use.")
    parser.add_argument("--date-str", type=str, required=True, help="Date string for the puzzle data (e.g., YYYY-MM-DD).")
    parser.add_argument("--logging-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Logging level (default: INFO).")
    parser.add_argument("--num_steps", type=int, default=50, help="Maximum number of steps for the solver (default: 50).")

    args = parser.parse_args()
    return args

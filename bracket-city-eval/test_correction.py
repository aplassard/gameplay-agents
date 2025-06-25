import argparse
import os
from pathlib import Path
import logging
import sys

# Add the parent directory to sys.path to allow imports from graph
sys.path.append(str(Path(__file__).resolve().parent))

# Now import the necessary functions from graph.py
# We will use the main parse_llm_response which includes the correction logic,
# and also the _parse_text_to_clue_answer for direct parsing of the corrected text if needed,
# and correct_llm_response if we want to test correction separately.
from graph import parse_llm_response, _parse_text_to_clue_answer, correct_llm_response
from llm_utils import call_llm_with_retry # This is needed by graph.py

# Configure logging for the test script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_correction_on_directory(errors_dir_path: Path, model_name: str):
    """
    Tests the LLM response correction mechanism on all .txt files in a directory.
    """
    if not errors_dir_path.is_dir():
        logging.error(f"Error: The path {errors_dir_path} is not a valid directory.")
        return

    error_files = list(errors_dir_path.glob("*.txt"))
    if not error_files:
        logging.info(f"No .txt files found in {errors_dir_path} to test.")
        return

    total_files = 0
    successfully_corrected_and_parsed = 0
    failed_to_correct_or_parse = 0

    logging.info(f"Starting correction test for files in: {errors_dir_path} using model: {model_name}")

    for error_file_path in error_files:
        total_files += 1
        logging.info(f"\n--- Processing file: {error_file_path.name} ---")

        with open(error_file_path, "r") as f:
            original_malformed_text = f.read()

        logging.info(f"Original Malformed Text:\n{original_malformed_text}")

        # Option 1: Test the full parse_llm_response (which includes correction)
        # This is a more integrated test.
        clue_id, answer = parse_llm_response(original_malformed_text, model_name)

        # The parse_llm_response function itself logs details about correction attempts.
        # Here, we just care about the final outcome for reporting.

        if clue_id is not None and answer is not None:
            successfully_corrected_and_parsed += 1
            logging.info(f"Successfully parsed after potential correction.")
            logging.info(f"  Clue ID: {clue_id}")
            logging.info(f"  Answer: {answer}")
            # If you need to see the *actual* corrected text that parse_llm_response used,
            # you would need to modify parse_llm_response to return it, or re-run correct_llm_response here.
            # For simplicity, this test relies on parse_llm_response's internal logging for that detail.
        else:
            failed_to_correct_or_parse += 1
            logging.warning(f"Failed to parse, even after correction attempt (if any occurred).")
            # To show what the correction attempt (if made) returned, we can call it explicitly.
            # This is for reporting purposes in this script.
            logging.info("Running correction function explicitly to see corrected output for this report:")
            corrected_text_for_report = correct_llm_response(original_malformed_text, model_name)
            if corrected_text_for_report:
                logging.info(f"Correction Attempt Output (for reporting):\n{corrected_text_for_report}")
                # And try parsing this reported corrected text
                c_clue_id, c_answer = _parse_text_to_clue_answer(corrected_text_for_report)
                if c_clue_id and c_answer:
                     logging.info(f"  Reported corrected text parsed to: clue_id='{c_clue_id}', answer='{c_answer}'")
                else:
                     logging.info("  Reported corrected text still did not parse cleanly.")
            else:
                logging.info("  Correction attempt (for reporting) returned no text or failed.")


    logging.info("\n--- Correction Test Summary ---")
    logging.info(f"Total files processed: {total_files}")
    logging.info(f"Successfully corrected and parsed: {successfully_corrected_and_parsed}")
    logging.info(f"Failed to correct/parse: {failed_to_correct_or_parse}")

def main():
    parser = argparse.ArgumentParser(description="Test LLM response correction on a directory of error files.")
    parser.add_argument(
        "--model_name",
        type=str,
        required=True,
        help="Name of the LLM model to use for correction attempts (e.g., 'gpt-4', 'claude-2')."
    )
    parser.add_argument(
        "--errors_dir",
        type=str,
        default="./parse-errors/",
        help="Directory containing .txt files with malformed LLM responses. Defaults to './parse-errors/' relative to graph.py."
    )

    args = parser.parse_args()

    # The errors_dir should be relative to the location of graph.py,
    # or an absolute path.
    # For consistency with how graph.py saves errors, we assume it's relative to the script's parent if not absolute.
    script_dir = Path(__file__).resolve().parent
    errors_dir_path = Path(args.errors_dir)
    if not errors_dir_path.is_absolute():
        errors_dir_path = script_dir / errors_dir_path

    # Ensure the parse-errors directory for graph.py exists, as it might be created by graph.py itself.
    # The test script reads from it.
    # graph_parse_errors_dir = script_dir / "parse-errors"
    # graph_parse_errors_dir.mkdir(parents=True, exist_ok=True)


    test_correction_on_directory(errors_dir_path, args.model_name)

if __name__ == "__main__":
    main()

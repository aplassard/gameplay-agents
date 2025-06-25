import os
import argparse
import sys
import logging

# Add the parent directory to sys.path to allow direct import of llm_utils and graph
# This assumes the script is run from within the bracket-city-eval directory or its parent
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

from llm_utils import heal_llm_output
from graph import parse_llm_response # Using the actual parser function

# Configure basic logging for the script
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Evaluate the LLM output healing function.")
    parser.add_argument(
        "--model-name",
        required=True,
        help="The name of the LLM model to use for the healing process."
    )
    parser.add_argument(
        "--print-errors",
        action="store_true",
        help="If present, print the details of each file that failed to be healed and parsed."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="If present, print the 'before' and 'after' text for every file processed."
    )
    args = parser.parse_args()

    error_dir = './bracket-city-eval/parse-errors/'
    if not os.path.isdir(error_dir):
        logger.error(f"Error directory not found: {error_dir}")
        # Also check one level up, in case script is run from repo root
        alt_error_dir = './parse-errors/'
        if os.path.isdir(alt_error_dir):
            error_dir = alt_error_dir
            logger.info(f"Found error directory at alternate path: {error_dir}")
        else:
            sys.exit(f"Error: The directory {error_dir} (or {alt_error_dir}) does not exist. Please create it and populate it with .txt files of parse errors.")


    total_files = 0
    fixed_files = 0
    failed_examples = []

    logger.info(f"Processing files from: {error_dir}")
    # Ensure we are only processing .txt files
    try:
        filenames = [f for f in os.listdir(error_dir) if f.endswith(".txt") and os.path.isfile(os.path.join(error_dir, f))]
    except FileNotFoundError:
        sys.exit(f"Error: The directory {error_dir} was not found during os.listdir().")


    if not filenames:
        logger.warning(f"No .txt files found in {error_dir}. Evaluation cannot proceed.")
        print(f"Final Score: 0 / 0 examples fixed.")
        return

    for filename in filenames:
        total_files += 1
        filepath = os.path.join(error_dir, filename)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original_text = f.read()
        except Exception as e:
            logger.error(f"Could not read file {filepath}: {e}")
            failed_examples.append({
                'filename': filename,
                'original': f"Error reading file: {e}",
                'healed': '',
                'error': str(e),
                'stage': 'read_file'
            })
            continue

        if args.verbose:
            logger.info(f"\n--- Processing: {filename} ---")
            logger.info(f"Original Text:\n{original_text}")

        try:
            healed_text = heal_llm_output(original_text, args.model_name)
            if args.verbose:
                logger.info(f"Healed Text:\n{healed_text}")
        except Exception as e_heal:
            logger.error(f"Error during healing for {filename}: {e_heal}")
            failed_examples.append({
                'filename': filename,
                'original': original_text,
                'healed': '', # Healing failed
                'error': str(e_heal),
                'stage': 'healing'
            })
            continue # Skip parsing if healing failed

        try:
            # parse_llm_response returns (clue_id, answer) or (None, None)
            clue_id, answer = parse_llm_response(healed_text)

            if clue_id and answer: # Both must be non-empty and not None
                fixed_files += 1
                if args.verbose:
                    logger.info(f"Successfully parsed: clue_id='{clue_id}', answer='{answer}'")
            else:
                # This case handles when parsing technically "succeeded" (no exception)
                # but didn't find both required fields.
                raise ValueError("Parsing returned incomplete data (clue_id or answer is missing/empty).")

        except Exception as e_parse:
            logger.warning(f"Failed to parse healed text for {filename}. Error: {e_parse}")
            failed_examples.append({
                'filename': filename,
                'original': original_text,
                'healed': healed_text,
                'error': str(e_parse),
                'stage': 'parsing'
            })

    print(f"\n--- Evaluation Complete ---")
    print(f"Final Score: {fixed_files} / {total_files} examples fixed.")

    if args.print_errors and failed_examples:
        print("\n--- Failed Examples ---")
        for failure in failed_examples:
            print(f"\nFilename: {failure['filename']}")
            print(f"Stage of Failure: {failure['stage']}")
            if failure['stage'] != 'read_file': # Original text might not be available if read failed
                print(f"Original Text:\n{failure['original']}")
            if failure['healed']: # Only print healed if it exists
                print(f"Healed Text (attempted):\n{failure['healed']}")
            print(f"Error: {failure['error']}")
    elif args.print_errors and not failed_examples and total_files > 0 :
        print("\nNo errors to print, all examples processed successfully or healing was effective!")
    elif args.print_errors and not failed_examples and total_files == 0:
        print("\nNo files were processed, so no errors to print.")


if __name__ == "__main__":
    main()

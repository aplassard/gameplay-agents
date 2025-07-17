#!/bin/bash

# This script runs the Wordle agent for all combinations of models and words.

# Example usage:
# ./run-wordle.sh "openai/gpt-4.1-mini,openai/gpt-4o" "hello,world,apple"

set -e

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <comma_separated_models> <comma_separated_words>"
  exit 1
fi

MODELS=$(echo $1 | tr "," " ")
WORDS=$(echo $2 | tr "," " ")

for model in $MODELS; do
  for word in $WORDS; do
    echo "Running Wordle with model: $model and word: $word"
    uv run python -m wordle_agent.main --model $model --word $word --turns 100
  done
done

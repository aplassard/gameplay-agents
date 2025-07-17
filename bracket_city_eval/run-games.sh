#!/bin/bash

# Define an array of the model strings to loop through
#models=("openai/gpt-4.1" "openai/gpt-4.1-mini" "openai/gpt-4.1-nano", deepseek/deepseek-r1:free)
#models=("openai/gpt-4.1-nano" "mistralai/mistral-small-3.2-24b-instruct:free" "moonshotai/kimi-dev-72b:free")
#models=("openai/o4-mini" "openai/o3-mini" "openai/o1-mini" "openai/gpt-4-turbo" "openai/gpt-3.5-turbo-16k")
#models=("anthropic/claude-3-haiku" "anthropic/claude-3.5-haiku-20241022" "anthropic/claude-sonnet-4" "anthropic/claude-3.7-sonnet" "anthropic/claude-3.7-sonnet:thinking")
#models=("deepseek/deepseek-r1" "deepseek/deepseek-chat" "deepseek/deepseek-prover-v2")
#models=("deepseek/deepseek-r1-distill-llama-70b" "deepseek/deepseek-r1-0528-qwen3-8b" "deepseek/deepseek-r1-distill-qwen-32b" "tngtech/deepseek-r1t-chimera:free")
#models=("x-ai/grok-3-mini" "x-ai/grok-2-1212" "x-ai/grok-3")
#models=("meta-llama/llama-4-maverick" "meta-llama/llama-4-scout")
#models=("google/gemma-3-4b-it" "google/gemini-flash-1.5-8b" "google/gemma-3-12b-it" "google/gemini-2.0-flash-lite-001" "google/gemini-flash-1.5" "google/gemma-3-27b-it" "google/gemini-2.0-flash-001" "google/gemini-2.5-flash" "google/gemini-2.5-pro" "google/gemini-2.5-flash-preview:thinking")
#models=("qwen/qwen3-8b" "qwen/qwen3-14b" "qwen/qwen3-30b-a3b" "qwen/qwen3-32b" "qwen/qwen3-235b-a22b")
models=("x-ai/grok-4")


echo "test"

# Loop over each model in the 'models' array
for model in "${models[@]}"; do
    echo "$model"
  # Start a second loop to iterate through the date range
  for i in  $(seq 12 24) 
  do
    date_str="2025-05-${i}"
    echo "$model $date_str"
    uv run python bracket_city_graph.py --model-name ${model} --date-str ${date_str} &
  done
done

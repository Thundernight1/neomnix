#!/bin/bash

# Configuration for Claude Code with Ollama Cloud
export ANTHROPIC_BASE_URL="https://ollama.com/api"
export ANTHROPIC_API_KEY=""
export ANTHROPIC_AUTH_TOKEN="ollama"

# Check if OLLAMA_API_KEY is set
# Check if OLLAMA_API_KEY is set, otherwise use the provided default
if [ -z "$OLLAMA_API_KEY" ]; then
    export OLLAMA_API_KEY="sk-user-VAapAHyF1T0fq36fo1a0HbSCZ8ADmaTb1FuYZKgzI1-HRwBUCAZkDxXqJfG1W-fxmrhae9PNabAKjPO-SlhZvYWIOyu04OcywbRbdWnThhThR8nhuJArNrDpuLqL_oVvwwA"
fi

echo "Starting Claude Code with Ollama Cloud..."
echo "Base URL: $ANTHROPIC_BASE_URL"
echo "Model: qwen3-coder (recommended)"

# Run Claude Code
# Use local installation
./node_modules/.bin/claude --model qwen3-coder "$@"

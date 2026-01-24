#!/bin/bash
# Filter out AI self-attribution patterns from PR bodies and commit messages
# Usage: ./filter-attribution.sh <input_file>

if [ -z "$1" ]; then
    echo "Usage: $0 <input_file>" >&2
    exit 1
fi

if [ ! -f "$1" ]; then
    echo "File not found: $1" >&2
    exit 1
fi

# Filter patterns for Claude, Gemini, Codex, Anthropic, OpenAI, Google AI
sed -E \
    -e '/Generated (with|by) \[?Claude/Id' \
    -e '/Generated (with|by) \[?Gemini/Id' \
    -e '/Generated (with|by) \[?Codex/Id' \
    -e '/Generated (with|by) \[?GPT/Id' \
    -e '/Generated (with|by) \[?OpenAI/Id' \
    -e '/Generated (with|by) \[?Anthropic/Id' \
    -e '/Generated (with|by) \[?Google AI/Id' \
    -e '/Co-Authored-By:.*Claude/Id' \
    -e '/Co-Authored-By:.*Gemini/Id' \
    -e '/Co-Authored-By:.*Codex/Id' \
    -e '/Co-Authored-By:.*GPT/Id' \
    -e '/Co-Authored-By:.*OpenAI/Id' \
    -e '/Co-Authored-By:.*Anthropic/Id' \
    -e '/Co-Authored-By:.*noreply@anthropic/Id' \
    -e '/Co-Authored-By:.*noreply@openai/Id' \
    -e '/🤖.*Claude/d' \
    -e '/🤖.*Gemini/d' \
    -e '/🤖.*Codex/d' \
    -e '/Written by AI/Id' \
    -e '/AI-generated/Id' \
    -e '/This (code|PR|commit) was (written|generated|created) by/Id' \
    "$1"

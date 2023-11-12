#!/usr/bin/env bash

# Watch for changes in files matching "bot/*py" and reload the bot

cd "$(dirname "$0")" || exit

# Check if entr is installed
if ! command -v entr &> /dev/null
then
  echo "entr could not be found"
  echo "Install it with your package manager like:"
  echo "apt-get install entr"
  echo "brew install entr"
  exit
fi
find ./bot -name '*.py' | entr -r poetry run python -m bot

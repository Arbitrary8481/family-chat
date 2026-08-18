#!/bin/sh

# Hardcoded defaults - edit these if needed
USERNAME1="Family Member 1"
USERNAME2="Family Member 2"
THEME="dark"

export USERNAME1 USERNAME2 THEME
# Without this, Python buffers stdout when it isn't attached to a
# terminal (always true in Docker) — print()/logging output can sit
# invisibly in that buffer instead of showing up in the add-on log
# viewer, which is exactly why errors weren't appearing.
export PYTHONUNBUFFERED=1

echo "Starting Family Chat server..."
python /app/app/server.py

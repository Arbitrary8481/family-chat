#!/bin/sh

# Hardcoded defaults - edit these if needed
USERNAME1="Family Member 1"
USERNAME2="Family Member 2"
THEME="dark"

export USERNAME1 USERNAME2 THEME

echo "Starting Family Chat server..."
python /app/app/server.py

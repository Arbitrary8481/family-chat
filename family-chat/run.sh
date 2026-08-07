#!/bin/bash

# Get options from config
USERNAME1=$(bashio::config 'username1' 2>/dev/null || echo "Family Member 1")
USERNAME2=$(bashio::config 'username2' 2>/dev/null || echo "Family Member 2")
THEME=$(bashio::config 'theme' 2>/dev/null || echo "dark")

export USERNAME1 USERNAME2 THEME

echo "Starting Family Chat server..."
python /app/app/server.py
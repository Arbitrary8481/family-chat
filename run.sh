#!/usr/bin/env bashio

# Get options from config
USERNAME1=$(bashio::config 'username1')
USERNAME2=$(bashio::config 'username2')
THEME=$(bashio::config 'theme')

export USERNAME1 USERNAME2 THEME

bashio::log.info "Starting Family Chat server..."
python /app/app/server.py

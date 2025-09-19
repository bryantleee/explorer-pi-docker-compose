#!/bin/bash

# Script to run the Meshtastic coordinator with the virtual environment
# Usage: ./run_coordinator.sh

cd "$(dirname "$0")"
source venv/bin/activate
python coordinator.py

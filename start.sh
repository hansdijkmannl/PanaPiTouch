#!/bin/bash
# PanaPiTouch Startup Script

# Change to application directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set display (for running from SSH or as service)
export DISPLAY="${DISPLAY:-:0}"

# Qt platform settings
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export QT_AUTO_SCREEN_SCALE_FACTOR=1

# Run application
python main.py "$@"


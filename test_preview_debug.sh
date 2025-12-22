#!/bin/bash
# Test script to debug preview widget issues

cd /home/admin/PanaPiTouch

# Kill any running instances
pkill -9 -f "python.*main.py" 2>/dev/null
sleep 1

# Activate venv and run with debug output
source venv/bin/activate

echo "=== Starting PanaPiTouch with debug logging ==="
echo "Watch for these key messages:"
echo "  - MainWindow._on_frame_received: got frame"
echo "  - PreviewWidget.update_frame: received frame"
echo "  - FrameWorker: messages about frame processing"
echo "  - Preview: processed frame / display updated"
echo ""
echo "Press Ctrl+C to stop"
echo "==="
echo ""

# Run and capture output
python main.py 2>&1 | grep -E "(frame|Frame|FPS|Preview|Widget|Worker)" --line-buffered --color=always

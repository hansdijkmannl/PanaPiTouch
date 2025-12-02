#!/bin/bash
# Script to simulate 10.5" 16:10 screen on 15.4" 16:9 display using xrandr
# Creates black bars on left/right by using a smaller framebuffer

# Target resolution: 1177x736 (16:10 aspect ratio)
# This matches the physical size of a 10.5" screen on the 15.4" display
TARGET_WIDTH=1177
TARGET_HEIGHT=736
NATIVE_WIDTH=1920
NATIVE_HEIGHT=1080

echo "Setting up 16:10 aspect ratio simulation using xrandr..."
echo "Simulating 10.5\" screen on 15.4\" display"
echo "Resolution: ${TARGET_WIDTH}x${TARGET_HEIGHT} (16:10) with black bars on sides"
echo ""

# Wait for display to be ready
sleep 2

# Get the primary output name
OUTPUT=$(xrandr --listmonitors 2>/dev/null | grep -oP '^\s*\d+:\s+\+\*?\K\S+' | head -1)
if [ -z "$OUTPUT" ]; then
    OUTPUT=$(xrandr | grep " connected" | head -1 | cut -d' ' -f1)
fi

if [ -z "$OUTPUT" ]; then
    echo "Error: Could not detect display output"
    exit 1
fi

echo "Detected output: $OUTPUT"

# Create custom mode for 16:10 resolution
# Use gtf to calculate modeline (gtf is more commonly available than cvt)
MODELINE=$(gtf $TARGET_WIDTH $TARGET_HEIGHT 60 2>/dev/null | grep Modeline | sed 's/Modeline //')
if [ -z "$MODELINE" ]; then
    echo "Error: Could not generate modeline. Trying alternative resolution..."
    # Try slightly different resolution if exact one fails
    MODELINE=$(gtf $((TARGET_WIDTH-1)) $TARGET_HEIGHT 60 2>/dev/null | grep Modeline | sed 's/Modeline //')
fi
MODELINE_NAME=$(echo "$MODELINE" | awk '{print $1}')

# Remove existing mode if it exists
xrandr --delmode "$OUTPUT" "$MODELINE_NAME" 2>/dev/null || true
xrandr --rmmode "$MODELINE_NAME" 2>/dev/null || true

# Add new mode
xrandr --newmode $MODELINE
xrandr --addmode "$OUTPUT" "$MODELINE_NAME"

# Calculate black bar size
OFFSET_X=$(( ($NATIVE_WIDTH - $TARGET_WIDTH) / 2 ))

echo "Applying resolution..."
echo "Active area: ${TARGET_WIDTH}x${TARGET_HEIGHT}"
echo "Black bars: ${OFFSET_X}px on each side"

# Set the mode with a larger framebuffer - this should create black bars
# The framebuffer size determines the total screen size
xrandr --output "$OUTPUT" --mode "$MODELINE_NAME" --fb ${NATIVE_WIDTH}x${NATIVE_HEIGHT} --panning ${NATIVE_WIDTH}x${NATIVE_HEIGHT}

echo ""
echo "=========================================="
echo "  Configuration Complete!"
echo "=========================================="
echo ""
echo "Display: ${NATIVE_WIDTH}x${NATIVE_HEIGHT} (16:9) - native"
echo "Active area: ${TARGET_WIDTH}x${TARGET_HEIGHT} (16:10) - simulated 10.5\" screen"
echo "Black bars: ~${OFFSET_X}px on each side"
echo ""
echo "Note: If black bars don't appear, the desktop environment may override this."
echo "You may need to configure your desktop environment's display settings."
echo ""


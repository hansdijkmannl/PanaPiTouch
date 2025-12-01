#!/bin/bash
# Add SSH key for passwordless login to Pi
# Run this on the Pi with your public key as argument

AUTHORIZED_KEYS="$HOME/.ssh/authorized_keys"

if [ -z "$1" ]; then
    echo "Usage: $0 'ssh-ed25519 AAAA... user@host'"
    echo ""
    echo "To get your public key, run this on YOUR computer:"
    echo "  cat ~/.ssh/id_ed25519.pub"
    echo "  (or cat ~/.ssh/id_rsa.pub)"
    echo ""
    echo "Then run this script with that key."
    exit 1
fi

# Add the key
echo "$1" >> "$AUTHORIZED_KEYS"
chmod 600 "$AUTHORIZED_KEYS"

echo "✓ SSH key added! You can now connect without password."


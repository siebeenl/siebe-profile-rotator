# ============================================================
#  SIEBE CONFIG ROTATOR
# ============================================================

# seconds before rotating
ROTATION_INTERVAL = 30

# Your online presence dot colour:
#   "online"   
#   "idle"     
#   "dnd"       
#   "invisible"
STATUS_TYPE = "dnd"

# Custom statuses to rotate through.
# Each entry has:
#   "emoji"  → unicode emoji shown left of the text, or None for no emoji
#   "text"   → the status text (max ~128 chars)
STATUSES = [
    {"emoji": "💻", "text": "Developer @ Dubai Roleplay"},
    {"emoji": "🎵", "text": ".gg/dubairoleplay"},
    {"emoji": "🥷", "text": "Cheats?"},
    {"emoji": "🆓", "text": "# Free Respectloos"},
]

# Set to True to rotate in random order instead of top-to-bottom
SHUFFLE = False

# Log file path — set to None to disable file logging
LOG_FILE = "status_rotator.log"

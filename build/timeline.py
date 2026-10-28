"""Shared timing for the Turning 65 in 2027 edit (HeyGen take).

Talking head: heygen/arric_heygen.mp4 (1080x1920, 25 fps, green #1CA331).
Word times come from a word-level transcript of that file; the edit has no cuts,
so source time == edited time.
"""

SRC_FILE = "heygen/arric_heygen.mp4"
KEY_COLOR = "0x1CA331"
SRC_END = 48.45
TAIL = 1.4      # hold last frame so the resolving chord can ring out
FPS = 30
W, H = 1080, 1920
SPLIT = int(H * 0.55)  # top 55% graphics stage / bottom 45% speaker

END = SRC_END + TAIL

# Scene starts
S1 = 0.0
S2 = 7.66                  # "I'm Arric Allen with Allen & Associates"
S3 = 10.05                 # "Medicare's annual election period..."
S4 = 18.10                 # "If your Medicare doesn't start until 2027"
S5 = 23.76                 # "Instead, your real timeline..."
S6 = 29.55                 # "Use that time to learn the two main paths"
S7 = 37.20                 # "To start reviewing your 2027 options early..."

# Word-synced beats
T_2027_SAID = 2.00
T_DO_NOT = 3.44
T_STATIC_OFF = 6.82        # "confuse you"
T_OCT15 = 12.54
T_DEC7 = 13.80
T_ONLY = 15.34
T_STAMP = 22.46            # "December seventh deadline"
T_GREEN = T_STAMP + 0.50
T_SIX_NINE = 26.82
T_TWO_PATHS = 31.04
T_PATH_A = 33.12           # "original Medicare..."
T_PATH_B = 36.08           # "Medicare Advantage"
T_DIGITS = [41.56, 42.66, 42.98, 43.28, 43.80, 44.08, 44.36, 44.64]  # 800, 3, 2, 4, 9, 9, 8, 6
T_URL = 46.22
T_CHORD = 48.38

# Speaker zoom per scene (Bottom-Center placement)
ZOOMS = [(S1, 1.00), (S2, 1.12), (S3, 1.00), (S4, 1.15), (S5, 1.00), (S6, 1.15), (S7, 1.05)]

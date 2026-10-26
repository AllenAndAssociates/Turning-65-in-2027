"""Shared timing for the Turning 65 in 2027 edit.

Source footage has a flubbed duplicate "I'm Arric Allen." at 8.10-11.18s.
It is cut out, so every source time after the cut shifts back by CUT_LEN.
All times below are on the EDITED timeline (seconds).
"""

CUT_IN = 8.10   # source time where the flub starts (cut here)
CUT_OUT = 11.18  # source time where the clean take resumes
CUT_LEN = CUT_OUT - CUT_IN
SRC_END = 55.317
TAIL = 1.4      # hold last frame so the resolving chord can ring out
FPS = 30
W, H = 1080, 1920
SPLIT = int(H * 0.55)  # top 55% graphics stage / bottom 45% speaker


def e(src):
    """Map a source timestamp (after the cut) to the edited timeline."""
    return src - CUT_LEN if src >= CUT_OUT else src


END = e(SRC_END) + TAIL

# Scene starts (edited timeline)
S1 = 0.0
S2 = CUT_IN                # "I'm Arric Allen with Allen & Associates"
S3 = e(14.14) - 0.25       # "Medicare's annual election period..."
S4 = e(22.32) - 0.25       # "If your Medicare doesn't start until 2027"
S5 = e(29.04) - 0.10       # "Instead, your real timeline..."
S6 = e(36.02) - 0.25       # "Use that time to learn the two main paths"
S7 = e(45.96) - 0.35       # "To start reviewing your 2027 options early..."

# Word-synced beats
T_2027_SAID = 2.60
T_DO_NOT = 4.12
T_STATIC_OFF = 7.06        # "confuse you"
T_OCT15 = e(16.96)
T_DEC7 = e(17.84)
T_ONLY = e(19.34)
T_STAMP = e(27.04)         # "December seventh deadline"
T_GREEN = e(27.04) + 0.50
T_SIX_NINE = e(31.58)
T_TWO_PATHS = e(38.20)
T_PATH_A = e(40.50)        # "original Medicare..."
T_PATH_B = e(43.58)        # "Medicare Advantage"
T_DIGITS = [e(t) for t in (49.48, 50.18, 50.42, 50.66, 50.96, 51.16, 51.34, 51.56)]
T_URL = e(52.82)
T_CHORD = e(54.88) + 0.05

# Speaker zoom per scene (Bottom-Center placement)
ZOOMS = [(S1, 1.00), (S2, 1.12), (S3, 1.00), (S4, 1.15), (S5, 1.00), (S6, 1.15), (S7, 1.05)]

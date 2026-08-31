"""
EXP187 Forensic Script: Pinpoint the exact root cause distinguishing
the 1,053 stall seeds from the 8,947 healthy seeds in FastSim.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import numpy as np

# We can run a focused Rust script that logs step-by-step state differences
# between 50 stall seeds and 50 healthy seeds.

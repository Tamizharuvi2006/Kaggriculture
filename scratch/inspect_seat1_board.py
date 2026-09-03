import sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_challenger_exp208_clean as challenger

experts = challenger._V18_RUNTIME["experts"]
board_p0 = challenger._V18_RUNTIME["board_by_seat"]["0"]
board_p1 = challenger._V18_RUNTIME["board_by_seat"]["1"]

print(f"Board on Seat 0: {board_p0}")
print(f"Board on Seat 1: {board_p1}")

print("\nSeat 0 actions (first 10 steps):")
for s in range(10):
    print(f"  Step {s}: {experts[board_p0]['actions'][s]}")

print("\nSeat 1 actions (first 10 steps):")
for s in range(10):
    print(f"  Step {s}: {experts[board_p1]['actions'][s]}")

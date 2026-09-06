import os, sys, json
import kaggle_environments

replays = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0, "Match 1"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json", 0, "Match 14"),
]

for rp, seat, label in replays:
    sys.path.insert(0, r"D:\kaggriculture")
    import submission_rc12
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    for s in range(12 * 24):
        obs = env.state[seat].observation
        act = submission_rc12.agent(obs)
        if s == 11 * 24: # Day 11 start
            print(f"\n--- {label} (Day 11) ---")
            print("Opponent Style:", submission_rc12._OPPONENT_STYLE)
            print("Expert Evidence:", submission_rc12._EXPERT_EVIDENCE)
            print("Expert Weights:", submission_rc12._expert_weights())
            print("Blended Targets:", submission_rc12._blended_targets())
            print("Strawberry Risk:", submission_rc12._POTENTIAL_STRAWBERRY_RISK)
            print("Flood Confirmed:", submission_rc12._FLOOD_CONFIRMED)
        if seat == 0:
            env.step([act, opp_actions[s]])
        else:
            env.step([opp_actions[s], act])

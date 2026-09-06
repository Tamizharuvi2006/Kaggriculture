import os, sys, json
import kaggle_environments

replays = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0, "Match 1"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json", 0, "Match 14"),
]

def check_destruction(rp, seat, label):
    sys.path.insert(0, r"D:\kaggriculture")
    import submission_rc6_d1
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[seat].observation
        day = obs["day"]
        if day in [11, 12, 13] and s % 24 == 0:
            farm = obs["farms"][seat]
            straw_tiles = [(x, y) for y, row in enumerate(farm["tiles"]) for x, t in enumerate(row) if isinstance(t, dict) and t.get("crop") == "STRAWBERRY"]
            animal_tiles = [(x, y, t.get("animal")) for y, row in enumerate(farm["tiles"]) for x, t in enumerate(row) if isinstance(t, dict) and t.get("kind") == "ANIMAL"]
            shed_animals = obs["private"]["shed"]
            print(f"[{label}] Day {day} Step {s}: {len(straw_tiles)} straw tiles | {len(animal_tiles)} animal tiles | shed: COW={shed_animals.get('COW', 0)}, SHEEP={shed_animals.get('SHEEP', 0)}")
        act = submission_rc6_d1.agent(obs)
        if seat == 0:
            env.step([act, opp_actions[s]])
        else:
            env.step([opp_actions[s], act])

for rp, seat, label in replays:
    check_destruction(rp, seat, label)

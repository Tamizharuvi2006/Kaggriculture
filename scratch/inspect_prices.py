import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments, json
import candidates.submission_adaptive_economic_v1 as cand

replay_file = r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json"
with open(replay_file) as f: rep = json.load(f)

opp_actions = [frame[1].get("action") for frame in rep["steps"][1:]]
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": rep["info"]["seed"]})
env.reset()

for s in range(len(opp_actions)):
    if env.done: break
    act = cand.agent(env.state[0].observation)
    env.step([act, opp_actions[s]])
    if s % 48 == 0:
        obs = env.state[0].observation
        prices = obs.get("market", {}).get("prices", {})
        p_straw = prices.get("STRAWBERRY")
        p_melon = prices.get("MELON")
        p_wheat = prices.get("WHEAT")
        p_milk = prices.get("MILK")
        print(f"Day {s//24:02d} Prices: Strawberry ${p_straw} | Melon ${p_melon} | Wheat ${p_wheat} | Milk ${p_milk}")

print("Cand V1 Final:", env.state[0].reward, "Opp:", env.state[1].reward)

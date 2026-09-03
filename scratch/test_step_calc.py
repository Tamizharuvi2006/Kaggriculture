def get_step(obs):
    s = obs.get("step")
    if s is not None:
        return int(s)
    d = int(obs.get("day", 0) or 0)
    h = int(obs.get("hour", 0) or 0)
    return d * 24 + h

obs_test = {"day": 5, "hour": 14}
print("get_step(obs_test):", get_step(obs_test)) # should be 5*24 + 14 = 134

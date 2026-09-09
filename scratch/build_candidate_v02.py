import os

def build_cand_v02():
    v41_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
    with open(v41_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Enable interference for v18 in agent(obs)
    # Find the use_interference block
    old_target = """            use_interference = (
                (version == "v12" and STRATEGY.get("v12_market_interference"))
                or (use_radiant and STRATEGY.get("v11_radiant_market_interference"))
                or (version not in {"v12", "v13", "v14", "v15", "v16", "v17", "v18"} and not use_radiant)
            )"""

    new_target = """            use_interference = (
                (version == "v18")
                or (version == "v12" and STRATEGY.get("v12_market_interference"))
                or (use_radiant and STRATEGY.get("v11_radiant_market_interference"))
                or (version not in {"v12", "v13", "v14", "v15", "v16", "v17", "v18"} and not use_radiant)
            )"""

    assert old_target in code, "Old interference block not found"
    code = code.replace(old_target, new_target, 1)

    os.makedirs(r"D:\kaggriculture\candidates", exist_ok=True)
    out_path = r"D:\kaggriculture\candidates\cand_v41_evolved_v02.py"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Successfully generated {out_path} ({len(code)} bytes)")

if __name__ == "__main__":
    build_cand_v02()

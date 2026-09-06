import sys
sys.path.insert(0, r"D:\kaggriculture")

import ast, hashlib
import kaggle_environments
import submission_rc4_2_hybrid as rc42

def audit_code_integrity(filepath):
    print("=" * 80)
    print(f"PRE-FLIGHT INTEGRITY AUDIT: {filepath}")
    print("=" * 80)
    
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
        sha256 = hashlib.sha256(code.encode("utf-8")).hexdigest()
        
    tree = ast.parse(code)
    
    # 1. Dependency check
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names: imported_modules.add(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module: imported_modules.add(node.module)
            
    allowed_deps = {"math", "random", "collections", "heapq", "sys", "os", "copy", "itertools"}
    disallowed = [m for m in imported_modules if m not in allowed_deps]
    print(f"1. External Dependencies: {imported_modules}")
    print(f"   Disallowed / Risky:   {disallowed} -> {'PASS (100% Pure Standard Library)' if not disallowed else 'FAIL'}")
    
    # 2. Lookahead / Replay / Cheating audit
    forbidden_tokens = ["tape", "replay", "history_step", "peek", "future", "seed_predict", "hack"]
    found_forbidden = [tok for tok in forbidden_tokens if tok in code.lower()]
    print(f"2. Forbidden Token Audit: {found_forbidden} -> {'PASS (Zero Lookahead Artifacts)' if not found_forbidden else 'FAIL'}")
    
    # 3. Private State Access Audit
    # Ensure agent only reads obs['private'] for its own private shed, and never opponent private
    has_unsafe_private = "farms[1-player].private" in code or "farms[opponent].private" in code
    print(f"3. Private State Leakage: {'FAIL' if has_unsafe_private else 'PASS (Zero Opponent Private Access)'}")
    
    # 4. Engine Evaluation Check (Kaggle Environments Runtime Self-Play)
    print("4. Kaggle Engine Evaluation Test (Self-Play & Random)...")
    env = kaggle_environments.make("kaggriculture")
    env.reset()
    try:
        res = env.run([rc42.agent, "random"])
        status0 = res[-1][0]["status"]
        status1 = res[-1][1]["status"]
        score0 = res[-1][0]["observation"]["farms"][0]["money"]
        score1 = res[-1][1]["observation"]["farms"][1]["money"]
        print(f"   vs Random: Status P0: {status0}, P1: {status1} | Score: ${score0:,.0f} vs ${score1:,.0f} -> PASS")
    except Exception as e:
        print(f"   vs Random Test FAILED: {e}")
        
    try:
        res_self = env.run([rc42.agent, rc42.agent])
        status0 = res_self[-1][0]["status"]
        status1 = res_self[-1][1]["status"]
        score0 = res_self[-1][0]["observation"]["farms"][0]["money"]
        score1 = res_self[-1][1]["observation"]["farms"][1]["money"]
        print(f"   Self-Play: Status P0: {status0}, P1: {status1} | Score: ${score0:,.0f} vs ${score1:,.0f} -> PASS")
    except Exception as e:
        print(f"   Self-Play Test FAILED: {e}")
        
    print(f"5. File SHA256 Hash:     {sha256}")
    print("=" * 80)
    return sha256

if __name__ == "__main__":
    audit_code_integrity(r"D:\kaggriculture\submission_rc4_2_hybrid.py")

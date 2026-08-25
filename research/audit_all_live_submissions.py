import json
import glob
import os

def audit_all_live_submissions():
    telemetry_dir = r"D:\Kaggriculture\reports\live_match_telemetry"
    files = glob.glob(os.path.join(telemetry_dir, "submission_*_episodes.json"))
    
    print(f"Found {len(files)} live telemetry files:\n")
    
    total_live_matches = 0
    total_live_wins = 0
    total_live_losses = 0
    total_live_ties = 0
    
    submission_records = []
    
    for f in sorted(files):
        with open(f, "r", encoding="utf-8") as jf:
            d = json.load(jf)
        
        sub_info = d.get("submission", {})
        sub_id = sub_info.get("id") or os.path.basename(f).split("_")[1]
        episodes = d.get("episodes", [])
        
        wins = 0
        losses = 0
        ties = 0
        total_our_score = 0
        total_opp_score = 0
        
        for ep in episodes:
            agents = ep.get("agents", [])
            if len(agents) == 2:
                a0, a1 = agents[0], agents[1]
                sub_id_int = int(sub_id) if str(sub_id).isdigit() else None
                our_agent = a0 if a0.get("submissionId") == sub_id_int else (a1 if a1.get("submissionId") == sub_id_int else None)
                opp_agent = a1 if a0.get("submissionId") == sub_id_int else (a0 if a1.get("submissionId") == sub_id_int else None)
                if our_agent and opp_agent:
                    our_rew = our_agent.get("reward", 0)
                    opp_rew = opp_agent.get("reward", 0)
                    total_our_score += our_rew
                    total_opp_score += opp_rew
                    if our_rew > opp_rew:
                        wins += 1
                    elif our_rew < opp_rew:
                        losses += 1
                    else:
                        ties += 1
                        
        n = wins + losses + ties
        wr = (wins / n * 100.0) if n > 0 else 0.0
        avg_our = (total_our_score / n) if n > 0 else 0.0
        avg_opp = (total_opp_score / n) if n > 0 else 0.0
        margin = avg_our - avg_opp
        
        submission_records.append({
            "sub_id": sub_id,
            "filename": os.path.basename(f),
            "matches": n,
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "win_rate": wr,
            "avg_score": avg_our,
            "avg_opp_score": avg_opp,
            "avg_margin": margin
        })
        
        total_live_matches += n
        total_live_wins += wins
        total_live_losses += losses
        total_live_ties += ties
        
    print("=" * 110)
    print(f"{'Submission ID':<16} | {'Matches':<8} | {'Wins':<6} | {'Losses':<7} | {'Ties':<5} | {'Win Rate':<9} | {'Avg Wealth':<12} | {'Avg Margin':<12}")
    print("=" * 110)
    for r in submission_records:
        print(f"{str(r['sub_id']):<16} | {r['matches']:<8} | {r['wins']:<6} | {r['losses']:<7} | {r['ties']:<5} | {r['win_rate']:>6.1f}%   | ${r['avg_score']:>10,.0f} | ${r['avg_margin']:>+10,.0f}")
    print("=" * 110)
    print(f"{'TOTAL LIVE MATCHES':<16} | {total_live_matches:<8} | {total_live_wins:<6} | {total_live_losses:<7} | {total_live_ties:<5} | {total_live_wins/total_live_matches*100:>6.1f}%")
    print("=" * 110)

if __name__ == "__main__":
    audit_all_live_submissions()

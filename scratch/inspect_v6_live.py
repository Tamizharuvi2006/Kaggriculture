import sys
sys.path.insert(0, r"D:\kaggriculture")

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

import live_dashboard

v6_sid = 55935415
episodes, sub_meta = live_dashboard.fetch_submission_episodes(v6_sid)
analysis = live_dashboard.analyze_matches(v6_sid, episodes)

elo_change = analysis['current_elo'] - analysis['initial_elo']

print("=" * 115)
print(f"       LIVE TELEMETRY DETAIL: EXP212 RESPONDER V6 (SUBMISSION #{v6_sid})                  ")
print("=" * 115)
print(f"Current Elo  : {analysis['current_elo']:.1f} (Rating Change: {elo_change:+.1f} from {analysis['initial_elo']:.1f})")
print(f"Total Matches: {analysis['matches_count']} ({analysis['wins']}W / {analysis['losses']}L / {analysis['ties']}T) | Win Rate: {analysis['win_rate']:.1f}%")
print(f"Hero Mean    : ${analysis['avg_hero']:,.0f} | Opponent Mean: ${analysis['avg_opp']:,.0f} | Margin: {analysis['avg_margin']:+,.0f}")

matches = analysis.get('matches', [])
if matches:
    hero_rewards = [m['hero_reward'] for m in matches]
    print(f"Highest Score: ${max(hero_rewards):,.0f} | Lowest Score: ${min(hero_rewards):,.0f}")

print("\n" + "-" * 115)
print(f"{'Episode ID':<12} | {'Result':<8} | {'Hero Wealth':<14} | {'Opp Wealth':<14} | {'Margin':<14} | {'Opp Elo':<10} | {'Seat':<5} | Date")
print("-" * 115)

for m in sorted(matches, key=lambda x: str(x.get('date', '')), reverse=True):
    res_str = "WIN" if m['result'] == "WIN" else "LOSS"
    date_str = str(m.get('date', ''))[:19]
    print(f"{m['episode_id']:<12} | {res_str:<8} | ${m['hero_reward']:12,.0f} | ${m['opp_reward']:12,.0f} | {m['delta']:+13,.0f} | {m['opp_elo']:8.0f}   | {m['hero_seat']:<5} | {date_str}")
print("=" * 115)

import pandas as pd

df = pd.read_csv("reports/phase14_ml_advisor_dataset.csv")

rep_summary = df.groupby("replay").agg(
    harmful_flood=("target_harmful_flood", "max"),
    opp_bushes_d11=("opp_straw_bushes", "first"),
    max_inv=("market_straw_inventory", "max"),
    min_p=("current_p_straw", "min")
).reset_index()

print("=" * 80)
print("REPLAY SUMMARY: HARMFUL STRAWBERRY SATURATION (P < $80 BEFORE DAY 22)")
print("=" * 80)
print(f"{'REPLAY':<35} | {'FLOOD?':>6} | {'OPP D11':>7} | {'MAX INV':>8} | {'MIN P':>8}")
print("-" * 80)
for _, r in rep_summary.iterrows():
    f_str = "YES" if r["harmful_flood"] == 1 else "NO"
    if r["harmful_flood"] == 1 or r["opp_bushes_d11"] >= 16:
        print(f"{r['replay']:<35} | {f_str:>6} | {r['opp_bushes_d11']:>7} | {r['max_inv']:>8,} | ${r['min_p']:>7.1f}")

print("=" * 80)
print(f"Total replays with harmful strawberry collapse: {rep_summary['harmful_flood'].sum()} out of {len(rep_summary)}")

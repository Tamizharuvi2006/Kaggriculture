import json, numpy as np
from scipy import stats

with open("reports/H6_THRESHOLD16_PAIRED_AUDIT.json") as f:
    d = json.load(f)

rc2 = np.array(d["rc2_scores"])
h6 = np.array(d["h6_scores"])
deltas = h6 - rc2

n = len(deltas)
mean_delta = np.mean(deltas)
median_delta = np.median(deltas)
std_delta = np.std(deltas, ddof=1)
se_delta = std_delta / np.sqrt(n)

# Paired t-test
t_stat, p_val_t = stats.ttest_rel(h6, rc2)

# Wilcoxon signed-rank test
w_stat, p_val_w = stats.wilcoxon(deltas[deltas != 0])

# Bootstrap 95% CI (10,000 resamples)
np.random.seed(42)
boot_means = [np.mean(np.random.choice(deltas, size=n, replace=True)) for _ in range(10000)]
ci_lower = np.percentile(boot_means, 2.5)
ci_upper = np.percentile(boot_means, 97.5)

pos = np.sum(deltas > 0)
neg = np.sum(deltas < 0)
zero = np.sum(deltas == 0)

print("=" * 70)
print("PAIRED STATISTICAL RIGOR AUDIT: H6-THRESHOLD16 vs RC2 CONTROL (N=20)")
print("=" * 70)
print(f"Mean Delta (H6 - RC2):        ${mean_delta:>+10,.2f}")
print(f"Median Delta:                 ${median_delta:>+10,.2f}")
print(f"Std Dev of Deltas:            ${std_delta:>10,.2f}")
print(f"Standard Error (SE):          ${se_delta:>10,.2f}")
print(f"Bootstrap 95% CI:             [${ci_lower:,.2f}, ${ci_upper:,.2f}]")
print(f"Paired t-test:                t = {t_stat:+.4f}, p = {p_val_t:.4f}")
print(f"Wilcoxon signed-rank test:    W = {w_stat:.1f}, p = {p_val_w:.4f}")
print(f"Win/Loss/Tie Distribution:    Positive: {pos} | Negative: {neg} | Zero: {zero}")
print("=" * 70)

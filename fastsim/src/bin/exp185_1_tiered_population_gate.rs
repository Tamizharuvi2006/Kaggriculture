//! EXP185.1 — Multi-Tier Live-Calibrated Population Promotion Gate.
//! Evaluates candidate policy against 4 calibrated rating tiers across held-out seeds with paired opponent differential.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, AdaptiveTerminalPolicy, D1Policy, V41Policy, MultiCropPlannerPolicy,
    EXP185_1_SparseGatedPolicy, SparseGatedConfig
};
use rayon::prelude::*;
use std::time::Instant;

#[derive(Default, Clone)]
pub struct TierResult {
    pub seed: u64,
    pub cand_score: f64,
    pub adap_score: f64,
    pub opp_score: f64,
}

pub fn run_paired_tier_match<C: Policy, A: Policy, O: Policy>(
    cand_policy: &C,
    adap_policy: &A,
    opp_policy: &O,
    seed: u64,
    cand_seat: usize,
) -> TierResult {
    // 1. Match 1: Candidate vs Opponent
    let mut state_cand = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    while !state_cand.done {
        let a_cand = cand_policy.act(&state_cand, cand_seat);
        let a_opp = opp_policy.act(&state_cand, 1 - cand_seat);

        let actions = if cand_seat == 0 { [a_cand, a_opp] } else { [a_opp, a_cand] };
        step_game(&mut state_cand, &actions);
    }
    let cand_score = state_cand.farms[cand_seat].money;
    let opp_score = state_cand.farms[1 - cand_seat].money;

    // 2. Match 2: Adaptive (Baseline) vs Same Opponent on Same Seed & Seat
    let mut state_adap = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    while !state_adap.done {
        let a_adap = adap_policy.act(&state_adap, cand_seat);
        let a_opp = opp_policy.act(&state_adap, 1 - cand_seat);

        let actions = if cand_seat == 0 { [a_adap, a_opp] } else { [a_opp, a_adap] };
        step_game(&mut state_adap, &actions);
    }
    let adap_score = state_adap.farms[cand_seat].money;

    TierResult {
        seed,
        cand_score,
        adap_score,
        opp_score,
    }
}

pub struct TierStats {
    pub tier_name: &'static str,
    pub elo_range: &'static str,
    pub total: usize,
    pub cand_wins_vs_opp: usize,
    pub adap_wins_vs_opp: usize,
    pub cand_mean: f64,
    pub adap_mean: f64,
    pub paired_delta: f64, // cand_mean - adap_mean
    pub cand_median: f64,
    pub adap_median: f64,
    pub cand_worst_5pct: f64,
    pub adap_worst_5pct: f64,
    pub cand_worst_1pct: f64,
    pub adap_worst_1pct: f64,
}

pub fn evaluate_tier<C: Policy + Send + Sync, A: Policy + Send + Sync, O: Policy + Send + Sync>(
    cand_factory: impl Fn() -> C + Sync + Send,
    adap_factory: impl Fn() -> A + Sync + Send,
    opp_factory: impl Fn() -> O + Sync + Send,
    tier_name: &'static str,
    elo_range: &'static str,
    seeds: &[u64],
) -> TierStats {
    let results: Vec<TierResult> = seeds.par_iter().map(|&seed| {
        let cand = cand_factory();
        let adap = adap_factory();
        let opp = opp_factory();
        // Alternate seat 0 and seat 1
        let seat = (seed % 2) as usize;
        run_paired_tier_match(&cand, &adap, &opp, seed, seat)
    }).collect();

    let n = results.len() as f64;
    let mut cand_wins = 0;
    let mut adap_wins = 0;

    let mut cand_scores = Vec::with_capacity(results.len());
    let mut adap_scores = Vec::with_capacity(results.len());
    let mut deltas = Vec::with_capacity(results.len());

    for r in &results {
        cand_scores.push(r.cand_score);
        adap_scores.push(r.adap_score);
        deltas.push(r.cand_score - r.adap_score);

        if r.cand_score > r.opp_score + 1.0 { cand_wins += 1; }
        if r.adap_score > r.opp_score + 1.0 { adap_wins += 1; }
    }

    let cand_mean = cand_scores.iter().sum::<f64>() / n;
    let adap_mean = adap_scores.iter().sum::<f64>() / n;
    let paired_delta = deltas.iter().sum::<f64>() / n;

    cand_scores.sort_by(|a, b| a.partial_cmp(b).unwrap());
    adap_scores.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let cand_median = cand_scores[results.len() / 2];
    let adap_median = adap_scores[results.len() / 2];

    let cand_worst_5pct = cand_scores[(results.len() as f64 * 0.05) as usize];
    let adap_worst_5pct = adap_scores[(results.len() as f64 * 0.05) as usize];

    let cand_worst_1pct = cand_scores[(results.len() as f64 * 0.01) as usize];
    let adap_worst_1pct = adap_scores[(results.len() as f64 * 0.01) as usize];

    TierStats {
        tier_name,
        elo_range,
        total: results.len(),
        cand_wins_vs_opp: cand_wins,
        adap_wins_vs_opp: adap_wins,
        cand_mean,
        adap_mean,
        paired_delta,
        cand_median,
        adap_median,
        cand_worst_5pct,
        adap_worst_5pct,
        cand_worst_1pct,
        adap_worst_1pct,
    }
}

fn print_tier_row(s: &TierStats) {
    let cand_wr = (s.cand_wins_vs_opp as f64 / s.total as f64) * 100.0;
    let adap_wr = (s.adap_wins_vs_opp as f64 / s.total as f64) * 100.0;

    println!("{:<24} | {:<12} | {:5.1}% vs {:5.1}% | ${:<8.0} vs ${:<8.0} | {:<+9.1} | ${:<7.0} vs ${:<7.0} | ${:<6.0} vs ${:<6.0}",
        s.tier_name, s.elo_range, cand_wr, adap_wr, s.cand_mean, s.adap_mean, s.paired_delta,
        s.cand_worst_5pct, s.adap_worst_5pct, s.cand_worst_1pct, s.adap_worst_1pct);
}

fn main() {
    println!("=========================================================================================================================");
    println!("             EXP185.1 — LIVE-CALIBRATED POPULATION TIER PROMOTION GATE (PAIRED HELD-OUT SEEDS)                           ");
    println!("=========================================================================================================================");

    let seeds: Vec<u64> = (10000..12000).collect(); // 2,000 completely fresh held-out seeds
    let t0 = Instant::now();

    let cand_cfg = SparseGatedConfig {
        max_interventions: 1,
        confidence_weighted: true,
        min_expected_gain: 300.0,
        min_prob_threshold: 0.25,
    };

    // Tier 1: Core Meta Clones (900-1000 Elo)
    println!("\n[Tier 1/4] Evaluating vs Core Meta Clones (V4.1)...");
    let stats_t1 = evaluate_tier(
        move || EXP185_1_SparseGatedPolicy::new("EXP185.1", cand_cfg),
        AdaptiveTerminalPolicy::new,
        V41Policy::new,
        "Tier 1: Core Clones", "900-1000 Elo", &seeds
    );

    // Tier 2: Dynamic Agro Hybrids (1000-1200 Elo) [CRITICAL]
    println!("[Tier 2/4] Evaluating vs Dynamic Agro Hybrids (MultiCrop)...");
    let stats_t2 = evaluate_tier(
        move || EXP185_1_SparseGatedPolicy::new("EXP185.1", cand_cfg),
        AdaptiveTerminalPolicy::new,
        MultiCropPlannerPolicy::new,
        "Tier 2: Agro Hybrids", "1000-1200 Elo", &seeds
    );

    // Tier 3: Grandmaster Replay Prototype (1200-1400 Elo)
    println!("[Tier 3/4] Evaluating vs Grandmaster Replay (D.1)...");
    let stats_t3 = evaluate_tier(
        move || EXP185_1_SparseGatedPolicy::new("EXP185.1", cand_cfg),
        AdaptiveTerminalPolicy::new,
        D1Policy::new,
        "Tier 3: Grandmaster D.1", "1200-1400 Elo", &seeds
    );

    // Tier 4: Competitive Peak Mirror (1400-1800+ Elo)
    println!("[Tier 4/4] Evaluating vs Competitive Peak (Adaptive Terminal)...");
    let stats_t4 = evaluate_tier(
        move || EXP185_1_SparseGatedPolicy::new("EXP185.1", cand_cfg),
        AdaptiveTerminalPolicy::new,
        AdaptiveTerminalPolicy::new,
        "Tier 4: Adaptive Peak", "1400-1800+ Elo", &seeds
    );

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nTiered Gate Evaluation Completed in {:.2}s ({:.1} paired matches/sec)\n", elapsed, (seeds.len() * 4 * 2) as f64 / elapsed);

    println!("=========================================================================================================================");
    println!("                                          TIERED POPULATION GATE SCORECARD                                               ");
    println!("=========================================================================================================================");
    println!("{:<24} | {:<12} | {:<17} | {:<20} | {:<9} | {:<17} | {:<15}",
        "Opponent Tier", "Rating Band", "WR (Cand vs Adap)", "Mean (Cand vs Adap)", "Net Δ", "5% Floor (C vs A)", "1% Floor (C vs A)");
    println!("-------------------------------------------------------------------------------------------------------------------------");
    print_tier_row(&stats_t1);
    print_tier_row(&stats_t2);
    print_tier_row(&stats_t3);
    print_tier_row(&stats_t4);
    println!("=========================================================================================================================");

    let total_paired_delta = (stats_t1.paired_delta + stats_t2.paired_delta + stats_t3.paired_delta + stats_t4.paired_delta) / 4.0;
    println!("\n>>> Overall Cross-Tier Paired Advantage (Candidate - Adaptive): {:+.2} <<<", total_paired_delta);
}

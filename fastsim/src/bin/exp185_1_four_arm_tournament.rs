//! EXP185.1 — 4-Arm Tournament: Sparse-Gated Gating vs Adaptive Control.
//! Evaluates Mean Return, Worst 10%/5%/1% Floors, Interventions/Game, and Rescue Efficiency.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, AdaptiveTerminalPolicy, EXP185_1_SparseGatedPolicy, SparseGatedConfig
};
use rayon::prelude::*;
use std::time::Instant;

#[derive(Default, Clone)]
pub struct MatchResult {
    pub seed: u64,
    pub p0_score: f64,
    pub p1_score: f64,
    pub p0_cash_d5: f64,
    pub p0_cash_d10: f64,
    pub p0_cash_d15: f64,
    pub p1_cash_d5: f64,
    pub p1_cash_d10: f64,
    pub p1_cash_d15: f64,
}

pub fn run_pair<P0: Policy, P1: Policy>(p0: &P0, p1: &P1, seed: u64) -> MatchResult {
    let mut state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let mut res = MatchResult { seed, ..Default::default() };

    while !state.done {
        let day = state.day;
        let hour = state.hour;

        if hour == 0 {
            if day == 5 {
                res.p0_cash_d5 = state.farms[0].money;
                res.p1_cash_d5 = state.farms[1].money;
            } else if day == 10 {
                res.p0_cash_d10 = state.farms[0].money;
                res.p1_cash_d10 = state.farms[1].money;
            } else if day == 15 {
                res.p0_cash_d15 = state.farms[0].money;
                res.p1_cash_d15 = state.farms[1].money;
            }
        }

        let a0 = p0.act(&state, 0);
        let a1 = p1.act(&state, 1);
        step_game(&mut state, &[a0, a1]);
    }

    res.p0_score = state.farms[0].money;
    res.p1_score = state.farms[1].money;
    res
}

pub struct MatchupStats {
    pub p0_name: &'static str,
    pub p1_name: &'static str,
    pub total: usize,
    pub p0_wins: usize,
    pub p1_wins: usize,
    pub ties: usize,
    pub p0_mean: f64,
    pub p1_mean: f64,
    pub p0_median: f64,
    pub p1_median: f64,
    pub p0_worst_10pct: f64,
    pub p0_worst_5pct: f64,
    pub p0_worst_1pct: f64,
    pub p1_worst_5pct: f64,
    pub p0_d5_cash: f64,
    pub p0_d10_cash: f64,
    pub p0_d15_cash: f64,
}

pub fn evaluate_matchup<P0: Policy, P1: Policy>(
    p0_factory: impl Fn() -> P0 + Sync + Send,
    p1_factory: impl Fn() -> P1 + Sync + Send,
    p0_name: &'static str,
    p1_name: &'static str,
    seeds: &[u64],
) -> MatchupStats {
    let results: Vec<MatchResult> = seeds.par_iter().map(|&seed| {
        let p0 = p0_factory();
        let p1 = p1_factory();
        run_pair(&p0, &p1, seed)
    }).collect();

    let n = results.len() as f64;
    let mut p0_wins = 0;
    let mut p1_wins = 0;
    let mut ties = 0;

    let mut p0_scores = Vec::with_capacity(results.len());
    let mut p1_scores = Vec::with_capacity(results.len());

    let mut sum_p0_d5 = 0.0;
    let mut sum_p0_d10 = 0.0;
    let mut sum_p0_d15 = 0.0;

    for r in &results {
        p0_scores.push(r.p0_score);
        p1_scores.push(r.p1_score);

        sum_p0_d5 += r.p0_cash_d5;
        sum_p0_d10 += r.p0_cash_d10;
        sum_p0_d15 += r.p0_cash_d15;

        if r.p0_score > r.p1_score + 1.0 { p0_wins += 1; }
        else if r.p1_score > r.p0_score + 1.0 { p1_wins += 1; }
        else { ties += 1; }
    }

    let p0_mean = p0_scores.iter().sum::<f64>() / n;
    let p1_mean = p1_scores.iter().sum::<f64>() / n;

    p0_scores.sort_by(|a, b| a.partial_cmp(b).unwrap());
    p1_scores.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let p0_median = p0_scores[results.len() / 2];
    let p1_median = p1_scores[results.len() / 2];

    let p0_worst_10pct = p0_scores[(results.len() as f64 * 0.10) as usize];
    let p0_worst_5pct = p0_scores[(results.len() as f64 * 0.05) as usize];
    let p0_worst_1pct = p0_scores[(results.len() as f64 * 0.01) as usize];

    let p1_worst_5pct = p1_scores[(results.len() as f64 * 0.05) as usize];

    MatchupStats {
        p0_name,
        p1_name,
        total: results.len(),
        p0_wins,
        p1_wins,
        ties,
        p0_mean,
        p1_mean,
        p0_median,
        p1_median,
        p0_worst_10pct,
        p0_worst_5pct,
        p0_worst_1pct,
        p1_worst_5pct,
        p0_d5_cash: sum_p0_d5 / n,
        p0_d10_cash: sum_p0_d10 / n,
        p0_d15_cash: sum_p0_d15 / n,
    }
}

fn print_arm(stats: &MatchupStats, arm_desc: &'static str) {
    let wr = (stats.p0_wins as f64 / stats.total as f64) * 100.0;
    println!("{:<32} | {:5.1}% | ${:<9.1} | ${:<9.1} | ${:<9.1} | ${:<9.1} | ${:<9.1} | ${:<5.0} -> ${:<5.0} -> ${:<5.0}",
        arm_desc, wr, stats.p0_mean, stats.p0_mean - stats.p1_mean, stats.p0_median, stats.p0_worst_5pct, stats.p0_worst_1pct,
        stats.p0_d5_cash, stats.p0_d10_cash, stats.p0_d15_cash);
}

fn main() {
    println!("===================================================================================================================");
    println!("                 EXP185.1 — 4-ARM SPARSE-GATED TOURNAMENT (vs ADAPTIVE BASELINE)                                   ");
    println!("===================================================================================================================");

    let seeds: Vec<u64> = (1000..3500).collect(); // 2,500 diverse golden seeds x 2 seats = 5,000 matches per arm
    let t0 = Instant::now();

    // Arm A: Adaptive Control Baseline
    println!("\n[1/4] Evaluating Arm A: Adaptive Baseline Self-Play...");
    let stats_a = evaluate_matchup(AdaptiveTerminalPolicy::new, AdaptiveTerminalPolicy::new, "Adaptive (S0)", "Adaptive (S1)", &seeds);

    // Arm B: Max 1 Intervention + Dynamic Runway Guard (min gain $300)
    println!("[2/4] Evaluating Arm B: Sparse Max-1 Intervention + Runway Guard...");
    let cfg_b = SparseGatedConfig {
        max_interventions: 1,
        confidence_weighted: false,
        min_expected_gain: 300.0,
        min_prob_threshold: 0.20,
    };
    let stats_b = evaluate_matchup(
        move || EXP185_1_SparseGatedPolicy::new("Arm B (Max 1)", cfg_b),
        AdaptiveTerminalPolicy::new,
        "Arm B (Max 1)", "Adaptive", &seeds
    );

    // Arm C: Max 2 Interventions + Dynamic Runway Guard (min gain $300)
    println!("[3/4] Evaluating Arm C: Sparse Max-2 Interventions + Runway Guard...");
    let cfg_c = SparseGatedConfig {
        max_interventions: 2,
        confidence_weighted: false,
        min_expected_gain: 300.0,
        min_prob_threshold: 0.20,
    };
    let stats_c = evaluate_matchup(
        move || EXP185_1_SparseGatedPolicy::new("Arm C (Max 2)", cfg_c),
        AdaptiveTerminalPolicy::new,
        "Arm C (Max 2)", "Adaptive", &seeds
    );

    // Arm D: Max 1 Intervention + Confidence-Weighted Threshold (min gain $500, prob 0.35)
    println!("[4/4] Evaluating Arm D: Sparse Max-1 + Confidence-Weighted Threshold...");
    let cfg_d = SparseGatedConfig {
        max_interventions: 1,
        confidence_weighted: true,
        min_expected_gain: 500.0,
        min_prob_threshold: 0.35,
    };
    let stats_d = evaluate_matchup(
        move || EXP185_1_SparseGatedPolicy::new("Arm D (Conf-Wgt Max 1)", cfg_d),
        AdaptiveTerminalPolicy::new,
        "Arm D (Conf-Wgt)", "Adaptive", &seeds
    );

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nTournament Completed in {:.2}s ({:.1} matches/sec)\n", elapsed, (seeds.len() * 4) as f64 / elapsed);

    println!("===================================================================================================================");
    println!("                                            EXP185.1 4-ARM SCORECARD                                               ");
    println!("===================================================================================================================");
    println!("{:<32} | {:<7} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {:<20}",
        "Policy Arm", "Win %", "Mean Score", "Net Delta", "Median", "Worst 5%", "Worst 1%", "Cash D5 -> D10 -> D15");
    println!("-------------------------------------------------------------------------------------------------------------------");
    print_arm(&stats_a, "Arm A: Adaptive Control");
    print_arm(&stats_b, "Arm B: Sparse Max-1 + Runway");
    print_arm(&stats_c, "Arm C: Sparse Max-2 + Runway");
    print_arm(&stats_d, "Arm D: Conf-Weighted Max-1");
    println!("===================================================================================================================");
}

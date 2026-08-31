//! EXP192 — 10,000-Match Head-to-Head Tournament & Multi-Tier Population Gate for EXP192 Verified Sheep Policy.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, AdaptiveTerminalPolicy, EXP192VerifiedSheepPolicy, D1Policy, V41Policy, MultiCropPlannerPolicy
};
use rayon::prelude::*;
use std::time::Instant;

#[derive(Default, Clone)]
pub struct MatchResult {
    pub seed: u64,
    pub p0_score: f64,
    pub p1_score: f64,
}

pub fn run_pair<P0: Policy, P1: Policy>(p0: &P0, p1: &P1, seed: u64) -> MatchResult {
    let mut state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let mut res = MatchResult { seed, ..Default::default() };

    while !state.done {
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
    pub p1_worst_1pct: f64,
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

    for r in &results {
        p0_scores.push(r.p0_score);
        p1_scores.push(r.p1_score);

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
    let p1_worst_1pct = p1_scores[(results.len() as f64 * 0.01) as usize];

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
        p1_worst_1pct,
    }
}


fn main() {
    println!("=========================================================================================================================");
    println!("     EXP192 — 10,000-MATCH HEAD-TO-HEAD TOURNAMENT: VERIFIED SHEEP POLICY vs ADAPTIVE TERMINAL                          ");
    println!("=========================================================================================================================");

    let seeds: Vec<u64> = (60000..65000).collect(); // 5,000 completely fresh seeds x 2 seats = 10,000 matches
    let t0 = Instant::now();

    // 1. EXP192 Verified (Seat 0) vs Adaptive (Seat 1)
    println!("\n[1/4] EXP192-Verified (Seat 0) vs Adaptive-Terminal (Seat 1)...");
    let stats_v_vs_a_s0 = evaluate_matchup(EXP192VerifiedSheepPolicy::new, AdaptiveTerminalPolicy::new, "EXP192-Verified", "Adaptive", &seeds);

    // 2. Adaptive (Seat 0) vs EXP192 Verified (Seat 1)
    println!("[2/4] Adaptive-Terminal (Seat 0) vs EXP192-Verified (Seat 1)...");
    let stats_v_vs_a_s1 = evaluate_matchup(AdaptiveTerminalPolicy::new, EXP192VerifiedSheepPolicy::new, "Adaptive", "EXP192-Verified", &seeds);

    // 3. EXP192 Verified vs D.1 Grandmaster
    println!("[3/4] EXP192-Verified (Seat 0) vs D.1 Grandmaster (Seat 1)...");
    let stats_v_vs_d1_s0 = evaluate_matchup(EXP192VerifiedSheepPolicy::new, D1Policy::new, "EXP192-Verified", "D.1", &seeds);

    println!("[4/4] D.1 Grandmaster (Seat 0) vs EXP192-Verified (Seat 1)...");
    let stats_v_vs_d1_s1 = evaluate_matchup(D1Policy::new, EXP192VerifiedSheepPolicy::new, "D.1", "EXP192-Verified", &seeds);

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nTournament Completed in {:.2}s ({:.1} matches/sec)\n", elapsed, (seeds.len() * 4) as f64 / elapsed);

    let combined_v_wins = stats_v_vs_a_s0.p0_wins + stats_v_vs_a_s1.p1_wins;
    let combined_a_wins = stats_v_vs_a_s0.p1_wins + stats_v_vs_a_s1.p0_wins;
    let combined_ties = stats_v_vs_a_s0.ties + stats_v_vs_a_s1.ties;
    let total_matches = seeds.len() * 2;

    let v_win_pct = (combined_v_wins as f64 / total_matches as f64) * 100.0;
    let a_win_pct = (combined_a_wins as f64 / total_matches as f64) * 100.0;
    let combined_delta = ((stats_v_vs_a_s0.p0_mean - stats_v_vs_a_s0.p1_mean) + (stats_v_vs_a_s1.p1_mean - stats_v_vs_a_s1.p0_mean)) / 2.0;

    println!("=========================================================================================================================");
    println!("                                   HEAD-TO-HEAD COMBINED SCORECARD (vs Adaptive)                                         ");
    println!("=========================================================================================================================");
    println!("EXP192-Verified Combined Win Rate: {:.2}% ({}/{})", v_win_pct, combined_v_wins, total_matches);
    println!("Adaptive-Terminal Win Rate       : {:.2}% ({}/{})", a_win_pct, combined_a_wins, total_matches);
    println!("Ties Rate                        : {:.2}% ({}/{})", (combined_ties as f64 / total_matches as f64) * 100.0, combined_ties, total_matches);
    println!("Net Delta Margin (Hero - Opp)    : {:+.2}", combined_delta);
    println!("EXP192 Worst 5% Floor            : ${:.1} (vs Adaptive Floor: ${:.1})", stats_v_vs_a_s0.p0_worst_5pct, stats_v_vs_a_s0.p1_worst_5pct);
    println!("EXP192 Worst 1% Floor            : ${:.1} (vs Adaptive Floor: ${:.1})", stats_v_vs_a_s0.p0_worst_1pct, stats_v_vs_a_s0.p1_worst_1pct);
    println!("=========================================================================================================================");

    // Combined vs D.1
    let combined_v_d1_wins = stats_v_vs_d1_s0.p0_wins + stats_v_vs_d1_s1.p1_wins;
    let v_d1_win_pct = (combined_v_d1_wins as f64 / total_matches as f64) * 100.0;
    println!("\n>>> EXP192-Verified Win Rate vs D.1 Grandmaster: {:.2}% ({}/{}) <<<", v_d1_win_pct, combined_v_d1_wins, total_matches);
}

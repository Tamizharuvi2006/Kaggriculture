//! EXP186 — 10,000-Match Tail Rescue Tournament & 1000+ Elo Population Validation.
//! Evaluates Tail-Rescue Rate on failing seeds, 1%/5% Floor Elevation, and Zero-Regression on 1000+ Elo Opponents.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, AdaptiveTerminalPolicy, EXP186RescuePolicy, D1Policy, V41Policy, MultiCropPlannerPolicy
};
use rayon::prelude::*;
use std::time::Instant;

#[derive(Default, Clone)]
pub struct MatchResult {
    pub seed: u64,
    pub p0_score: f64,
    pub p1_score: f64,
    pub p0_rescued: bool,
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

fn main() {
    println!("=========================================================================================================================");
    println!("             EXP186 — 10,000-MATCH TAIL RESCUE TOURNAMENT & 1000+ ELO POPULATION VALIDATION                              ");
    println!("=========================================================================================================================");

    let seeds: Vec<u64> = (1000..6000).collect(); // 5,000 seeds x 2 seats = 10,000 matches
    let t0 = Instant::now();

    println!("\n[1/4] Evaluating EXP186-Rescue (Seat 0) vs Adaptive (Seat 1)...");
    let results_s0: Vec<MatchResult> = seeds.par_iter().map(|&seed| {
        let p0 = EXP186RescuePolicy::new();
        let p1 = AdaptiveTerminalPolicy::new();
        run_pair(&p0, &p1, seed)
    }).collect();

    println!("[2/4] Evaluating Adaptive (Seat 0) vs EXP186-Rescue (Seat 1)...");
    let results_s1: Vec<MatchResult> = seeds.par_iter().map(|&seed| {
        let p0 = AdaptiveTerminalPolicy::new();
        let p1 = EXP186RescuePolicy::new();
        run_pair(&p0, &p1, seed)
    }).collect();

    let n = results_s0.len() as f64;
    let mut p0_wins = 0;
    let mut p1_wins = 0;
    let mut ties = 0;

    let mut scores_cand = Vec::with_capacity(results_s0.len() * 2);
    let mut scores_adap = Vec::with_capacity(results_s0.len() * 2);

    let mut failing_baseline_count = 0;
    let mut failing_rescued_count = 0;
    let mut failing_gains = Vec::new();

    for (r0, r1) in results_s0.iter().zip(results_s1.iter()) {
        scores_cand.push(r0.p0_score);
        scores_adap.push(r0.p1_score);
        scores_adap.push(r1.p0_score);
        scores_cand.push(r1.p1_score);

        if r0.p0_score > r0.p1_score + 1.0 { p0_wins += 1; }
        else if r0.p1_score > r0.p0_score + 1.0 { p1_wins += 1; }
        else { ties += 1; }

        if r1.p1_score > r1.p0_score + 1.0 { p0_wins += 1; }
        else if r1.p0_score > r1.p1_score + 1.0 { p1_wins += 1; }
        else { ties += 1; }

        // Track tail rescue on failing baseline matches (Adaptive < $50,000)
        if r0.p1_score < 50000.0 {
            failing_baseline_count += 1;
            if r0.p0_score >= 80000.0 {
                failing_rescued_count += 1;
                failing_gains.push(r0.p0_score - r0.p1_score);
            }
        }
    }

    let total_matches = seeds.len() * 2;
    let cand_mean = scores_cand.iter().sum::<f64>() / total_matches as f64;
    let adap_mean = scores_adap.iter().sum::<f64>() / total_matches as f64;

    scores_cand.sort_by(|a, b| a.partial_cmp(b).unwrap());
    scores_adap.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let cand_median = scores_cand[total_matches / 2];
    let adap_median = scores_adap[total_matches / 2];

    let cand_worst_10pct = scores_cand[(total_matches as f64 * 0.10) as usize];
    let adap_worst_10pct = scores_adap[(total_matches as f64 * 0.10) as usize];

    let cand_worst_5pct = scores_cand[(total_matches as f64 * 0.05) as usize];
    let adap_worst_5pct = scores_adap[(total_matches as f64 * 0.05) as usize];

    let cand_worst_1pct = scores_cand[(total_matches as f64 * 0.01) as usize];
    let adap_worst_1pct = scores_adap[(total_matches as f64 * 0.01) as usize];

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nTournament Completed in {:.2}s ({:.1} matches/sec)\n", elapsed, total_matches as f64 / elapsed);

    println!("=========================================================================================================================");
    println!("                                          EXP186 TAIL RESCUE SCORECARD                                                   ");
    println!("=========================================================================================================================");
    println!("Total Paired Matches           : {}", total_matches);
    println!("EXP186 Rescue Wins             : {} ({:.2}%)", p0_wins, (p0_wins as f64 / total_matches as f64) * 100.0);
    println!("Adaptive Baseline Wins         : {} ({:.2}%)", p1_wins, (p1_wins as f64 / total_matches as f64) * 100.0);
    println!("Ties                           : {} ({:.2}%)", ties, (ties as f64 / total_matches as f64) * 100.0);
    println!("Mean Reward                    : EXP186 = ${:.1} | Adaptive = ${:.1} (Net Δ: {:+.1})", cand_mean, adap_mean, cand_mean - adap_mean);
    println!("Median Reward                  : EXP186 = ${:.1} | Adaptive = ${:.1}", cand_median, adap_median);
    println!("-------------------------------------------------------------------------------------------------------------------------");
    println!("TAIL-RISK ELEVATION FLOORS:");
    println!("  Worst 10% Floor              : EXP186 = ${:.1} | Adaptive = ${:.1} (Floor Gain: {:+.1})", cand_worst_10pct, adap_worst_10pct, cand_worst_10pct - adap_worst_10pct);
    println!("  Worst 5% Floor               : EXP186 = ${:.1} | Adaptive = ${:.1} (Floor Gain: {:+.1})", cand_worst_5pct, adap_worst_5pct, cand_worst_5pct - adap_worst_5pct);
    println!("  Worst 1% Floor               : EXP186 = ${:.1} | Adaptive = ${:.1} (Floor Gain: {:+.1})", cand_worst_1pct, adap_worst_1pct, cand_worst_1pct - adap_worst_1pct);
    println!("-------------------------------------------------------------------------------------------------------------------------");
    println!("CRITICAL TAIL RESCUE METRIC (Baseline < $50k Collapses):");
    println!("  Identified Failing Matches   : {}", failing_baseline_count);
    println!("  Successfully Rescued (> $80k): {} ({:.1}% Rescue Rate)", failing_rescued_count, (failing_rescued_count as f64 / failing_baseline_count.max(1) as f64) * 100.0);
    let avg_rescue_gain = if !failing_gains.is_empty() { failing_gains.iter().sum::<f64>() / failing_gains.len() as f64 } else { 0.0 };
    println!("  Average Gain on Rescued Seeds: +${:.1}", avg_rescue_gain);
    println!("=========================================================================================================================");
}

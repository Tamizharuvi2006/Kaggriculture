//! EXP184-B — 10,000-Match Residual Q Tournament: AdaptiveTerminal vs Residual-Q-Adaptive.
//! Evaluates head-to-head win rates, mean delta, median reward, and tail-risk floors.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy, ResidualQAdaptivePolicy, D1Policy};
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
    pub p0_worst_5pct: f64,
    pub p1_worst_5pct: f64,
    pub p0_d5_cash: f64,
    pub p0_d10_cash: f64,
    pub p0_d15_cash: f64,
    pub p1_d5_cash: f64,
    pub p1_d10_cash: f64,
    pub p1_d15_cash: f64,
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

    let mut sum_p1_d5 = 0.0;
    let mut sum_p1_d10 = 0.0;
    let mut sum_p1_d15 = 0.0;

    for r in &results {
        p0_scores.push(r.p0_score);
        p1_scores.push(r.p1_score);

        sum_p0_d5 += r.p0_cash_d5;
        sum_p0_d10 += r.p0_cash_d10;
        sum_p0_d15 += r.p0_cash_d15;

        sum_p1_d5 += r.p1_cash_d5;
        sum_p1_d10 += r.p1_cash_d10;
        sum_p1_d15 += r.p1_cash_d15;

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

    let p0_worst_5pct = p0_scores[(results.len() as f64 * 0.05) as usize];
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
        p0_worst_5pct,
        p1_worst_5pct,
        p0_d5_cash: sum_p0_d5 / n,
        p0_d10_cash: sum_p0_d10 / n,
        p0_d15_cash: sum_p0_d15 / n,
        p1_d5_cash: sum_p1_d5 / n,
        p1_d10_cash: sum_p1_d10 / n,
        p1_d15_cash: sum_p1_d15 / n,
    }
}

fn print_stats(stats: &MatchupStats) {
    let p0_wr = (stats.p0_wins as f64 / stats.total as f64) * 100.0;
    let p1_wr = (stats.p1_wins as f64 / stats.total as f64) * 100.0;
    let tie_wr = (stats.ties as f64 / stats.total as f64) * 100.0;

    println!("-----------------------------------------------------------------------------------------");
    println!("Matchup: {} (Seat 0) vs {} (Seat 1) [{} Matches]", stats.p0_name, stats.p1_name, stats.total);
    println!("-----------------------------------------------------------------------------------------");
    println!("Outcome       : {} Wins: {} ({:.1}%) | {} Wins: {} ({:.1}%) | Ties: {} ({:.1}%)",
        stats.p0_name, stats.p0_wins, p0_wr, stats.p1_name, stats.p1_wins, p1_wr, stats.ties, tie_wr);
    println!("Mean Reward   : {} = ${:.1} | {} = ${:.1} (Delta: ${:.1})",
        stats.p0_name, stats.p0_mean, stats.p1_name, stats.p1_mean, stats.p0_mean - stats.p1_mean);
    println!("Median Reward : {} = ${:.1} | {} = ${:.1}",
        stats.p0_name, stats.p0_median, stats.p1_name, stats.p1_median);
    println!("Worst 5% Floor: {} = ${:.1} | {} = ${:.1}",
        stats.p0_name, stats.p0_worst_5pct, stats.p1_name, stats.p1_worst_5pct);
    println!("Cash Trajectory (D5 -> D10 -> D15):");
    println!("  {:<16} : ${:.0} -> ${:.0} -> ${:.0}", stats.p0_name, stats.p0_d5_cash, stats.p0_d10_cash, stats.p0_d15_cash);
    println!("  {:<16} : ${:.0} -> ${:.0} -> ${:.0}", stats.p1_name, stats.p1_d5_cash, stats.p1_d10_cash, stats.p1_d15_cash);
    println!();
}

fn main() {
    println!("=========================================================================================");
    println!("       EXP184-B TOURNAMENT: ADAPTIVE TERMINAL vs RESIDUAL-Q-ADAPTIVE (10,000 MATCHES)   ");
    println!("=========================================================================================");

    let seeds: Vec<u64> = (1000..6000).collect(); // 5,000 diverse seeds x 2 seats = 10,000 matches
    let t0 = Instant::now();

    // 1. Residual-Q-Adaptive vs AdaptiveTerminal (Seat 0 vs Seat 1)
    println!("\n[1/2] Residual-Q-Adaptive (Seat 0) vs AdaptiveTerminal (Seat 1)...");
    let stats_q_vs_adap_s0 = evaluate_matchup(ResidualQAdaptivePolicy::new, AdaptiveTerminalPolicy::new, "Residual-Q", "Adaptive", &seeds);

    // 2. AdaptiveTerminal vs Residual-Q-Adaptive (Seat 0 vs Seat 1 - Seat Swapped)
    println!("[2/2] AdaptiveTerminal (Seat 0) vs Residual-Q-Adaptive (Seat 1)...");
    let stats_q_vs_adap_s1 = evaluate_matchup(AdaptiveTerminalPolicy::new, ResidualQAdaptivePolicy::new, "Adaptive", "Residual-Q", &seeds);

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nTournament Completed in {:.2}s ({:.1} matches/sec)\n", elapsed, (seeds.len() * 2) as f64 / elapsed);

    println!("=========================================================================================");
    println!("                                   HEAD-TO-HEAD RESULTS                                  ");
    println!("=========================================================================================");
    print_stats(&stats_q_vs_adap_s0);
    print_stats(&stats_q_vs_adap_s1);

    let combined_q_wins = stats_q_vs_adap_s0.p0_wins + stats_q_vs_adap_s1.p1_wins;
    let combined_adap_wins = stats_q_vs_adap_s0.p1_wins + stats_q_vs_adap_s1.p0_wins;
    let combined_ties = stats_q_vs_adap_s0.ties + stats_q_vs_adap_s1.ties;
    let total_matches = seeds.len() * 2;

    let q_win_pct = (combined_q_wins as f64 / total_matches as f64) * 100.0;
    let adap_win_pct = (combined_adap_wins as f64 / total_matches as f64) * 100.0;
    let combined_delta = ((stats_q_vs_adap_s0.p0_mean - stats_q_vs_adap_s0.p1_mean) + (stats_q_vs_adap_s1.p1_mean - stats_q_vs_adap_s1.p0_mean)) / 2.0;

    println!("=========================================================================================");
    println!("                         SEAT-BALANCED COMBINED SCORECARD                                ");
    println!("=========================================================================================");
    println!("Residual-Q Combined Win Rate : {:.2}% ({}/{})", q_win_pct, combined_q_wins, total_matches);
    println!("Adaptive Combined Win Rate   : {:.2}% ({}/{})", adap_win_pct, combined_adap_wins, total_matches);
    println!("Ties Rate                    : {:.2}% ({}/{})", (combined_ties as f64 / total_matches as f64) * 100.0, combined_ties, total_matches);
    println!("Net Delta Margin (Hero - Opp): +${:.2}", combined_delta);
    println!("=========================================================================================");
}

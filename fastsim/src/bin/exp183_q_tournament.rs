//! EXP183 — 10k Four-Arm Q-Guided Tournament & Physical Execution Validation.
//! Evaluates Arms A, B, C, D across paired seeds with complete diagnostic scorecard.

use fastsim::engine::state::GameState;
use fastsim::engine::step::{step_game, PlayerAction};
use fastsim::policies::{
    Policy, AdaptiveTerminalPolicy, HierarchicalBCPolicy, QGuidedDispatcherPolicy, ModelBasedRolloutPolicy
};
use rayon::prelude::*;
use std::time::Instant;

#[derive(Default, Clone)]
pub struct MatchScorecard {
    pub seed: u64,
    pub arm_name: &'static str,
    pub hero_score: f64,
    pub opp_score: f64,
    pub won: bool,
    pub tied: bool,
    pub lost: bool,
    pub cash_d4: f64,
    pub cash_d7: f64,
    pub cash_d11: f64,
    pub cash_d15: f64,
    pub workers_d4: usize,
    pub workers_d7: usize,
    pub workers_d11: usize,
    pub workers_d15: usize,
    pub q2_day: Option<usize>,
    pub q3_day: Option<usize>,
}

pub fn run_match<P: Policy>(hero_policy: &P, opp_policy: &AdaptiveTerminalPolicy, seed: u64) -> MatchScorecard {
    let mut state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let mut card = MatchScorecard {
        seed,
        arm_name: hero_policy.name(),
        ..Default::default()
    };

    while !state.done {
        let step = state.step;
        let day = state.day;
        let hour = state.hour;

        // Snapshot diagnostic milestones at hour 0
        if hour == 0 {
            let hero_money = state.farms[0].money;
            let hero_hands = state.farms[0].hands.len();
            let quads = state.farms[0].unlocked_quadrants.len();

            if day == 4 { card.cash_d4 = hero_money; card.workers_d4 = hero_hands; }
            if day == 7 { card.cash_d7 = hero_money; card.workers_d7 = hero_hands; }
            if day == 11 { card.cash_d11 = hero_money; card.workers_d11 = hero_hands; }
            if day == 15 { card.cash_d15 = hero_money; card.workers_d15 = hero_hands; }

            if quads >= 2 && card.q2_day.is_none() { card.q2_day = Some(day); }
            if quads >= 3 && card.q3_day.is_none() { card.q3_day = Some(day); }
        }

        let a0 = hero_policy.act(&state, 0);
        let a1 = opp_policy.act(&state, 1);
        step_game(&mut state, &[a0, a1]);
    }

    card.hero_score = state.farms[0].money;
    card.opp_score = state.farms[1].money;

    if card.hero_score > card.opp_score { card.won = true; }
    else if (card.hero_score - card.opp_score).abs() < 1e-3 { card.tied = true; }
    else { card.lost = true; }

    card
}

#[derive(Default)]
pub struct ArmSummary {
    pub name: &'static str,
    pub matches: usize,
    pub wins: usize,
    pub ties: usize,
    pub losses: usize,
    pub mean_hero_score: f64,
    pub mean_opp_score: f64,
    pub mean_delta: f64,
    pub mean_cash_d4: f64,
    pub mean_cash_d7: f64,
    pub mean_cash_d11: f64,
    pub mean_cash_d15: f64,
    pub mean_workers_d4: f64,
    pub mean_workers_d7: f64,
    pub mean_workers_d11: f64,
    pub mean_workers_d15: f64,
}

pub fn summarize_cards(name: &'static str, cards: &[MatchScorecard]) -> ArmSummary {
    let n = cards.len() as f64;
    let mut sum = ArmSummary {
        name,
        matches: cards.len(),
        ..Default::default()
    };

    for c in cards {
        if c.won { sum.wins += 1; }
        if c.tied { sum.ties += 1; }
        if c.lost { sum.losses += 1; }
        sum.mean_hero_score += c.hero_score;
        sum.mean_opp_score += c.opp_score;
        sum.mean_delta += (c.hero_score - c.opp_score);
        sum.mean_cash_d4 += c.cash_d4;
        sum.mean_cash_d7 += c.cash_d7;
        sum.mean_cash_d11 += c.cash_d11;
        sum.mean_cash_d15 += c.cash_d15;
        sum.mean_workers_d4 += c.workers_d4 as f64;
        sum.mean_workers_d7 += c.workers_d7 as f64;
        sum.mean_workers_d11 += c.workers_d11 as f64;
        sum.mean_workers_d15 += c.workers_d15 as f64;
    }

    sum.mean_hero_score /= n;
    sum.mean_opp_score /= n;
    sum.mean_delta /= n;
    sum.mean_cash_d4 /= n;
    sum.mean_cash_d7 /= n;
    sum.mean_cash_d11 /= n;
    sum.mean_cash_d15 /= n;
    sum.mean_workers_d4 /= n;
    sum.mean_workers_d7 /= n;
    sum.mean_workers_d11 /= n;
    sum.mean_workers_d15 /= n;

    sum
}

fn main() {
    println!("================================================================================");
    println!("EXP183 — 4-ARM Q-GUIDED POLICY TOURNAMENT & PHYSICAL EXECUTION VALIDATION");
    println!("================================================================================");

    let num_seeds = 2500; // 2,500 seeds x 4 arms = 10,000 matches
    let seeds: Vec<u64> = (1000..(1000 + num_seeds as u64)).collect();

    println!("Evaluating 4 Arms across {} Golden Seeds (10,000 total paired games)...", num_seeds);
    let t0 = Instant::now();

    // Arm A: AdaptiveTerminal (Control baseline)
    println!("\n[1/4] Evaluating Arm A: AdaptiveTerminal (Control)...");
    let cards_a: Vec<MatchScorecard> = seeds.par_iter().map(|&seed| {
        let hero = AdaptiveTerminalPolicy::new();
        let opp = AdaptiveTerminalPolicy::new();
        run_match(&hero, &opp, seed)
    }).collect();
    let sum_a = summarize_cards("Arm A: AdaptiveTerminal", &cards_a);

    // Arm B: Hierarchical BC Policy
    println!("[2/4] Evaluating Arm B: Hierarchical BC Policy...");
    let cards_b: Vec<MatchScorecard> = seeds.par_iter().map(|&seed| {
        let hero = HierarchicalBCPolicy::new();
        let opp = AdaptiveTerminalPolicy::new();
        run_match(&hero, &opp, seed)
    }).collect();
    let sum_b = summarize_cards("Arm B: Hierarchical BC", &cards_b);

    // Arm C: Q-Guided Direct Policy
    println!("[3/4] Evaluating Arm C: Q-Guided Direct (Argmax Q)...");
    let cards_c: Vec<MatchScorecard> = seeds.par_iter().map(|&seed| {
        let hero = QGuidedDispatcherPolicy::new();
        let opp = AdaptiveTerminalPolicy::new();
        run_match(&hero, &opp, seed)
    }).collect();
    let sum_c = summarize_cards("Arm C: Q-Guided Direct", &cards_c);

    // Arm D: Model-Based Rollout Policy (BC + Top-K Q + FastSim Rollout)
    println!("[4/4] Evaluating Arm D: Model-Based Rollout (Top-K Q + FastSim)...");
    let cards_d: Vec<MatchScorecard> = seeds.par_iter().map(|&seed| {
        let hero = ModelBasedRolloutPolicy::new();
        let opp = AdaptiveTerminalPolicy::new();
        run_match(&hero, &opp, seed)
    }).collect();
    let sum_d = summarize_cards("Arm D: Model-Based Rollout", &cards_d);

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nTournament Completed in {:.2}s ({:.1} matches/sec)\n", elapsed, 10000.0 / elapsed);

    println!("=========================================================================================");
    println!("                               EXP183 TOURNAMENT SCORECARD                               ");
    println!("=========================================================================================");
    println!("{:<28} | {:<7} | {:<10} | {:<10} | {:<10} | {:<10}", "Policy", "Win %", "Hero Reward", "Opp Reward", "Mean Delta", "W / T / L");
    println!("-----------------------------------------------------------------------------------------");
    for sum in &[&sum_a, &sum_b, &sum_c, &sum_d] {
        let win_pct = (sum.wins as f64 / sum.matches as f64) * 100.0;
        println!("{:<28} | {:5.1}% | ${:<9.1} | ${:<9.1} | ${:<9.1} | {}/{}/{}",
            sum.name, win_pct, sum.mean_hero_score, sum.mean_opp_score, sum.mean_delta, sum.wins, sum.ties, sum.losses);
    }
    println!("=========================================================================================");

    println!("\n--- Physical & Economic Trajectory Comparison ---");
    println!("{:<28} | {:<8} | {:<8} | {:<8} | {:<8} | {:<6} | {:<6}", "Policy", "Day 4 $", "Day 7 $", "Day 11 $", "Day 15 $", "Wkr D7", "Wkr D15");
    println!("-----------------------------------------------------------------------------------------");
    for sum in &[&sum_a, &sum_b, &sum_c, &sum_d] {
        println!("{:<28} | ${:<7.0} | ${:<7.0} | ${:<7.0} | ${:<7.0} | {:<6.1} | {:<6.1}",
            sum.name, sum.mean_cash_d4, sum.mean_cash_d7, sum.mean_cash_d11, sum.mean_cash_d15, sum.mean_workers_d7, sum.mean_workers_d15);
    }
    println!("=========================================================================================");
}

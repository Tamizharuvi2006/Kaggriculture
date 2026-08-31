//! EXP207 — 40,000-Match Multi-Opponent 3000+ Tournament Benchmark.
//! Evaluates EXP205 Frontier Policy against 4 distinct authentic 3000+ tournament replay bots.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, EXP205FrontierPolicy,
    Elite3000OpponentA, Elite3000OpponentB, Elite3000OpponentC, Elite3000OpponentD
};
use rayon::prelude::*;
use std::time::Instant;

pub struct Multi3000Result {
    pub name: &'static str,
    pub replay_id: &'static str,
    pub peak_wealth: &'static str,
    pub total: usize,
    pub hero_wins: usize,
    pub opp_wins: usize,
    pub ties: usize,
    pub hero_mean: f64,
    pub opp_mean: f64,
    pub hero_worst_5pct: f64,
    pub opp_worst_5pct: f64,
    pub hero_worst_1pct: f64,
}

pub fn run_3000_eval<OppFactory, Opp>(
    opp_factory: OppFactory,
    name: &'static str,
    replay_id: &'static str,
    peak_wealth: &'static str,
    seeds: &[u64],
) -> Multi3000Result
where
    OppFactory: Fn() -> Opp + Sync + Send,
    Opp: Policy + 'static,
{
    // Seat 0: Hero, Seat 1: Opponent
    let s0_res: Vec<(f64, f64)> = seeds.par_iter().map(|&seed| {
        let hero = EXP205FrontierPolicy::new();
        let opp = opp_factory();
        let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !st.done {
            let a0 = hero.act(&st, 0);
            let a1 = opp.act(&st, 1);
            step_game(&mut st, &[a0, a1]);
        }
        (st.farms[0].money, st.farms[1].money)
    }).collect();

    // Seat 0: Opponent, Seat 1: Hero
    let s1_res: Vec<(f64, f64)> = seeds.par_iter().map(|&seed| {
        let opp = opp_factory();
        let hero = EXP205FrontierPolicy::new();
        let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !st.done {
            let a0 = opp.act(&st, 0);
            let a1 = hero.act(&st, 1);
            step_game(&mut st, &[a0, a1]);
        }
        (st.farms[1].money, st.farms[0].money) // (Hero, Opp)
    }).collect();

    let mut all_hero = Vec::with_capacity(seeds.len() * 2);
    let mut all_opp = Vec::with_capacity(seeds.len() * 2);
    let mut hero_wins = 0;
    let mut opp_wins = 0;
    let mut ties = 0;

    for &(h, o) in s0_res.iter().chain(s1_res.iter()) {
        all_hero.push(h);
        all_opp.push(o);
        if h > o + 1.0 { hero_wins += 1; }
        else if o > h + 1.0 { opp_wins += 1; }
        else { ties += 1; }
    }

    let n = all_hero.len() as f64;
    let hero_mean = all_hero.iter().sum::<f64>() / n;
    let opp_mean = all_opp.iter().sum::<f64>() / n;

    all_hero.sort_by(|a, b| a.partial_cmp(b).unwrap());
    all_opp.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let hero_worst_5pct = all_hero[(n * 0.05) as usize];
    let opp_worst_5pct = all_opp[(n * 0.05) as usize];
    let hero_worst_1pct = all_hero[(n * 0.01) as usize];

    Multi3000Result {
        name,
        replay_id,
        peak_wealth,
        total: all_hero.len(),
        hero_wins,
        opp_wins,
        ties,
        hero_mean,
        opp_mean,
        hero_worst_5pct,
        opp_worst_5pct,
        hero_worst_1pct,
    }
}

fn main() {
    println!("=========================================================================================================================");
    println!("     EXP207 — 40,000-MATCH MULTI-OPPONENT 3000+ BENCHMARK (4 DISTINCT REPLAY BOTS)                                       ");
    println!("=========================================================================================================================");

    let seeds_per_opp = 5000; // 5,000 seeds x 2 seats = 10,000 matches per opponent x 4 opponents = 40,000 matches
    let t0 = Instant::now();

    let b0_seeds: Vec<u64> = (960000..965000).collect();
    let b1_seeds: Vec<u64> = (965000..970000).collect();
    let b2_seeds: Vec<u64> = (970000..975000).collect();
    let b3_seeds: Vec<u64> = (975000..980000).collect();

    println!("[1/4] Evaluating Opponent A (Replay 91278544: Full 6-Phase Compounder, Peak $155,777)...");
    let r0 = run_3000_eval(Elite3000OpponentA::new, "Opponent A", "91278544.json", "$155,777", &b0_seeds);

    println!("[2/4] Evaluating Opponent B (Replay 91282058: Melon Specialization + Sheep, Peak $129,852)...");
    let r1 = run_3000_eval(Elite3000OpponentB::new, "Opponent B", "91282058.json", "$129,852", &b1_seeds);

    println!("[3/4] Evaluating Opponent C (Replay 91300882: Rapid Fertilizer Liquidation, Peak $128,990)...");
    let r2 = run_3000_eval(Elite3000OpponentC::new, "Opponent C", "91300882.json", "$128,990", &b2_seeds);

    println!("[4/4] Evaluating Opponent D (Replay 91304426: High-Cash Land Expansion, Peak $117,150)...");
    let r3 = run_3000_eval(Elite3000OpponentD::new, "Opponent D", "91304426.json", "$117,150", &b3_seeds);

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nAll 40,000 Matches Completed in {:.2}s ({:.1} matches/sec)\n", elapsed, 40000.0 / elapsed);

    println!("=========================================================================================================================");
    println!("                                   EXP207 40,000-MATCH MULTI-3000+ SCORECARD                                             ");
    println!("=========================================================================================================================");
    println!("{:<14} | {:<16} | {:<12} | {:<24} | {:<12} | {:<12} | {:<12}",
        "Opponent ID", "Replay File", "Peak Wealth", "Win / Tie / Loss", "Hero Mean", "Opp Mean", "Net Delta");
    println!("-------------------------------------------------------------------------------------------------------------------------");

    let mut total_hero_wins = 0;
    let mut total_opp_wins = 0;
    let mut total_ties = 0;
    let mut total_matches = 0;

    for r in &[&r0, &r1, &r2, &r3] {
        let wr = (r.hero_wins as f64 / r.total as f64) * 100.0;
        let tr = (r.ties as f64 / r.total as f64) * 100.0;
        let lr = (r.opp_wins as f64 / r.total as f64) * 100.0;
        let delta = r.hero_mean - r.opp_mean;

        total_hero_wins += r.hero_wins;
        total_opp_wins += r.opp_wins;
        total_ties += r.ties;
        total_matches += r.total;

        println!("{:<14} | {:<16} | {:<12} | {:>4.1}% / {:>3.1}% / {:>4.1}% | ${:<11.1} | ${:<11.1} | {:>+11.1}",
            r.name, r.replay_id, r.peak_wealth, wr, tr, lr, r.hero_mean, r.opp_mean, delta);
    }
    println!("-------------------------------------------------------------------------------------------------------------------------");
    let combined_wr = (total_hero_wins as f64 / total_matches as f64) * 100.0;
    let combined_lr = (total_opp_wins as f64 / total_matches as f64) * 100.0;
    let combined_tr = (total_ties as f64 / total_matches as f64) * 100.0;
    println!("COMBINED 3000+ POPULATION OVERALL: {:>4.1}% Wins ({}) / {:>3.1}% Ties / {:>4.1}% Losses ({})",
        combined_wr, total_hero_wins, combined_tr, combined_lr, total_opp_wins);
    println!("=========================================================================================================================");
}

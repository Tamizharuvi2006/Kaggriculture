//! EXP206 — 50,000-Match Elite Ladder Multi-Band Benchmark (1800 to 3000+ Rating Bands).
//! Evaluates EXP205 Frontier Policy against authentic High-Elo Opponent Populations.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, AdaptiveTerminalPolicy, EXP205FrontierPolicy,
    Elite1800_2200Policy, Elite2200_2600Policy, Elite2600_3000Policy, Elite3000PlusApexPolicy
};
use rayon::prelude::*;
use std::time::Instant;

pub struct BandResult {
    pub name: &'static str,
    pub elo_range: &'static str,
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

pub fn run_band_evaluation<OppFactory, Opp>(
    opp_factory: OppFactory,
    band_name: &'static str,
    elo_range: &'static str,
    seeds: &[u64],
) -> BandResult
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

    BandResult {
        name: band_name,
        elo_range,
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
    println!("     EXP206 — 50,000-MATCH ELITE LADDER BENCHMARK (1800 TO 3000+ POPULATION BANDS)                                        ");
    println!("=========================================================================================================================");

    let seeds_per_band = 5000; // 5,000 seeds x 2 seats = 10,000 matches per band x 5 bands = 50,000 matches
    let t0 = Instant::now();

    let b0_seeds: Vec<u64> = (900000..905000).collect();
    let b1_seeds: Vec<u64> = (905000..910000).collect();
    let b2_seeds: Vec<u64> = (910000..915000).collect();
    let b3_seeds: Vec<u64> = (915000..920000).collect();
    let b4_seeds: Vec<u64> = (920000..925000).collect();

    println!("[1/5] Evaluating Band 0 (1400–1800+ Elo: Adaptive Peak Baseline)...");
    let r0 = run_band_evaluation(AdaptiveTerminalPolicy::new, "Band 0: Adaptive Peak", "1400–1800+", &b0_seeds);

    println!("[2/5] Evaluating Band 1 (1800–2200 Elo: Elite Strawberry/Cow Compounders)...");
    let r1 = run_band_evaluation(Elite1800_2200Policy::new, "Band 1: Strawberry Scaler", "1800–2200", &b1_seeds);

    println!("[3/5] Evaluating Band 2 (2200–2600 Elo: Rapid Agro-Livestock Scalers)...");
    let r2 = run_band_evaluation(Elite2200_2600Policy::new, "Band 2: Agro-Livestock", "2200–2600", &b2_seeds);

    println!("[4/5] Evaluating Band 3 (2600–3000 Elo: High-Liquidity Melon/Sheep Grandmasters)...");
    let r3 = run_band_evaluation(Elite2600_3000Policy::new, "Band 3: Melon Grandmaster", "2600–3000", &b3_seeds);

    println!("[5/5] Evaluating Band 4 (3000+ Elo: Top-Ladder Apex Champions)...");
    let r4 = run_band_evaluation(Elite3000PlusApexPolicy::new, "Band 4: Apex Champion", "3000+ Apex", &b4_seeds);

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nAll 50,000 Matches Completed in {:.2}s ({:.1} matches/sec)\n", elapsed, 50000.0 / elapsed);

    println!("=========================================================================================================================");
    println!("                                   EXP206 50,000-MATCH ELITE POPULATION SCORECARD                                        ");
    println!("=========================================================================================================================");
    println!("{:<24} | {:<10} | {:<24} | {:<12} | {:<12} | {:<12} | {:<12}",
        "Opponent Rating Band", "Elo Band", "Win / Tie / Loss", "Hero Mean", "Opp Mean", "Net Delta", "Worst 5% Floor");
    println!("-------------------------------------------------------------------------------------------------------------------------");

    for r in &[&r0, &r1, &r2, &r3, &r4] {
        let wr = (r.hero_wins as f64 / r.total as f64) * 100.0;
        let tr = (r.ties as f64 / r.total as f64) * 100.0;
        let lr = (r.opp_wins as f64 / r.total as f64) * 100.0;
        let delta = r.hero_mean - r.opp_mean;

        println!("{:<24} | {:<10} | {:>4.1}% / {:>3.1}% / {:>4.1}% | ${:<11.1} | ${:<11.1} | {:>+11.1} | ${:<11.1}",
            r.name, r.elo_range, wr, tr, lr, r.hero_mean, r.opp_mean, delta, r.hero_worst_5pct);
    }
    println!("=========================================================================================================================");
}

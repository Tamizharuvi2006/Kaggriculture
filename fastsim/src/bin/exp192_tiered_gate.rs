//! EXP192 — Multi-Tier Population Gate (16,000 Paired Matches across 4 Rating Tiers).

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, EXP192VerifiedSheepPolicy, AdaptiveTerminalPolicy, D1Policy, V41Policy, MultiCropPlannerPolicy
};
use rayon::prelude::*;
use std::time::Instant;

pub struct TierResult {
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
}

pub fn run_tier_eval<OppFactory, Opp>(
    opp_factory: OppFactory,
    tier_name: &'static str,
    elo_range: &'static str,
    seeds: &[u64],
) -> TierResult
where
    OppFactory: Fn() -> Opp + Sync + Send,
    Opp: Policy + 'static,
{
    // Seat 0
    let s0_res: Vec<(f64, f64)> = seeds.par_iter().map(|&seed| {
        let hero = EXP192VerifiedSheepPolicy::new();
        let opp = opp_factory();
        let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !st.done {
            let a0 = hero.act(&st, 0);
            let a1 = opp.act(&st, 1);
            step_game(&mut st, &[a0, a1]);
        }
        (st.farms[0].money, st.farms[1].money)
    }).collect();

    // Seat 1
    let s1_res: Vec<(f64, f64)> = seeds.par_iter().map(|&seed| {
        let opp = opp_factory();
        let hero = EXP192VerifiedSheepPolicy::new();
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

    TierResult {
        name: tier_name,
        elo_range,
        total: all_hero.len(),
        hero_wins,
        opp_wins,
        ties,
        hero_mean,
        opp_mean,
        hero_worst_5pct,
        opp_worst_5pct,
    }
}

fn main() {
    println!("=========================================================================================");
    println!("     EXP192 — MULTI-TIER POPULATION PROMOTION GATE (16,000 PAIRED MATCHES)               ");
    println!("=========================================================================================");

    let seeds: Vec<u64> = (70000..72000).collect(); // 2,000 held-out seeds x 2 seats x 4 tiers = 16,000 matches
    let t0 = Instant::now();

    println!("[1/4] Evaluating Tier 1 (900–1000 Elo: V4.1 Clones)...");
    let t1 = run_tier_eval(V41Policy::new, "Tier 1: Core Clones", "900–1000", &seeds);

    println!("[2/4] Evaluating Tier 2 (1000–1200 Elo: Multi-Crop Agro)...");
    let t2 = run_tier_eval(MultiCropPlannerPolicy::new, "Tier 2: Agro Hybrids", "1000–1200", &seeds);

    println!("[3/4] Evaluating Tier 3 (1200–1400 Elo: D.1 Grandmaster)...");
    let t3 = run_tier_eval(D1Policy::new, "Tier 3: GM Prototypes", "1200–1400", &seeds);

    println!("[4/4] Evaluating Tier 4 (1400–1800+ Elo: Adaptive Terminal)...");
    let t4 = run_tier_eval(AdaptiveTerminalPolicy::new, "Tier 4: Adaptive Peak", "1400–1800+", &seeds);

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nMulti-Tier Promotion Gate Completed in {:.2}s ({:.1} matches/sec)\n", elapsed, 16000.0 / elapsed);

    println!("=========================================================================================================================");
    println!("                                   EXP192 MULTI-TIER SCORECARD                                                           ");
    println!("=========================================================================================================================");
    println!("{:<24} | {:<10} | {:<24} | {:<12} | {:<12} | {:<12} | {:<12}",
        "Tier & Opponent", "Elo Band", "Win / Tie / Loss", "Hero Mean", "Opp Mean", "Net Delta", "Worst 5% Floor");
    println!("-------------------------------------------------------------------------------------------------------------------------");

    for t in &[&t1, &t2, &t3, &t4] {
        let wr = (t.hero_wins as f64 / t.total as f64) * 100.0;
        let tr = (t.ties as f64 / t.total as f64) * 100.0;
        let lr = (t.opp_wins as f64 / t.total as f64) * 100.0;
        let delta = t.hero_mean - t.opp_mean;

        println!("{:<24} | {:<10} | {:>4.1}% / {:>3.1}% / {:>4.1}% | ${:<11.1} | ${:<11.1} | {:>+11.1} | ${:<11.1}",
            t.name, t.elo_range, wr, tr, lr, t.hero_mean, t.opp_mean, delta, t.hero_worst_5pct);
    }
    println!("=========================================================================================================================");
}

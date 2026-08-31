//! EXP210 — 40,000-Match Adversarial Stress Gate for EXP208 Champion Policy.
//! Evaluates EXP208 against 4 highly hostile opponent archetypes.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, EXP208ChampionPolicy,
    AdversarialHardMirror, AdversarialAgroLivestock, AdversarialApexGrandmaster, AdversarialMarketPredator
};
use rayon::prelude::*;
use std::time::Instant;

pub struct StressResult {
    pub name: &'static str,
    pub stress_category: &'static str,
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

pub fn run_stress_eval<OppFactory, Opp>(
    opp_factory: OppFactory,
    name: &'static str,
    stress_category: &'static str,
    seeds: &[u64],
) -> StressResult
where
    OppFactory: Fn() -> Opp + Sync + Send,
    Opp: Policy + 'static,
{
    // Seat 0: Hero, Seat 1: Opponent
    let s0_res: Vec<(f64, f64)> = seeds.par_iter().map(|&seed| {
        let hero = EXP208ChampionPolicy::new();
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
        let hero = EXP208ChampionPolicy::new();
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

    StressResult {
        name,
        stress_category,
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
    println!("     EXP210 — 40,000-MATCH ADVERSARIAL STRESS GATE (EXP208 CHAMPION POLICY)                                              ");
    println!("=========================================================================================================================");

    let seeds_s1: Vec<u64> = (1200000..1205000).collect(); // 10,000 matches
    let seeds_s2: Vec<u64> = (1205000..1210000).collect(); // 10,000 matches
    let seeds_s3: Vec<u64> = (1210000..1215000).collect(); // 10,000 matches
    let seeds_s4: Vec<u64> = (1215000..1220000).collect(); // 10,000 matches

    let t0 = Instant::now();

    println!("[1/4] Stress Test 1: Hard Mirror Opponent (Symmetric Micro-Liquidity Extraction)...");
    let r1 = run_stress_eval(AdversarialHardMirror::new, "Hard Mirror Opponent", "Symmetric Liquidity", &seeds_s1);

    println!("[2/4] Stress Test 2: Hyper-Aggressive Agro-Livestock (Day 2 Double Worker + Day 5 Land)...");
    let r2 = run_stress_eval(AdversarialAgroLivestock::new, "Agro-Livestock Scaler", "Aggressive Early Land", &seeds_s2);

    println!("[3/4] Stress Test 3: Top 3000+ Apex Grandmaster (Full Replay 6-Stage Compounder)...");
    let r3 = run_stress_eval(AdversarialApexGrandmaster::new, "Apex Grandmaster", "Full 6-Stage Apex", &seeds_s3);

    println!("[4/4] Stress Test 4: Market-Pressure Predator (High-Frequency Commodity Deflation)...");
    let r4 = run_stress_eval(AdversarialMarketPredator::new, "Market Predator", "Deflationary Pressure", &seeds_s4);

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nAll 40,000 Stress Matches Completed in {:.2}s ({:.1} matches/sec)\n", elapsed, 40000.0 / elapsed);

    println!("=========================================================================================================================");
    println!("                                   EXP210 40,000-MATCH ADVERSARIAL SCORECARD                                             ");
    println!("=========================================================================================================================");
    println!("{:<24} | {:<22} | {:<24} | {:<12} | {:<12} | {:<12} | {:<12}",
        "Opponent Matchup", "Stress Dynamic", "Win / Tie / Loss", "Hero Mean", "Opp Mean", "Net Delta", "Worst 5% Floor");
    println!("-------------------------------------------------------------------------------------------------------------------------");

    let mut all_pass = true;

    for r in &[&r1, &r2, &r3, &r4] {
        let wr = (r.hero_wins as f64 / r.total as f64) * 100.0;
        let tr = (r.ties as f64 / r.total as f64) * 100.0;
        let lr = (r.opp_wins as f64 / r.total as f64) * 100.0;
        let delta = r.hero_mean - r.opp_mean;

        if wr < 50.0 || delta < 0.0 || r.hero_worst_5pct < 40000.0 {
            all_pass = false;
        }

        println!("{:<24} | {:<22} | {:>4.1}% / {:>3.1}% / {:>4.1}% | ${:<11.1} | ${:<11.1} | {:>+11.1} | ${:<11.1}",
            r.name, r.stress_category, wr, tr, lr, r.hero_mean, r.opp_mean, delta, r.hero_worst_5pct);
    }
    println!("-------------------------------------------------------------------------------------------------------------------------");
    println!("EXP210 ADVERSARIAL GATE VERDICT: {}", if all_pass { "🟢 PASSED (100% POSITIVE ALPHA ACROSS ALL ADVERSARIAL STRESSORS)" } else { "🔴 FAILED" });
    println!("=========================================================================================================================");
}

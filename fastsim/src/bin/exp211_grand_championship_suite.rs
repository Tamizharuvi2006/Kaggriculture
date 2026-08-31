//! EXP211 — 100,000-Match Grand Championship Pre-Upload Certification Suite.
//! Tests EXP208 Champion Policy pairwise against the 10 most formidable baseline and elite opponents
//! using common random numbers, exact 720-step FastSim simulation, and seat balancing.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, AdaptiveTerminalPolicy, D1Policy, V41Policy,
    EXP204EliteBCPolicy, EXP205FrontierPolicy, EXP208ChampionPolicy,
    Elite2200_2600Policy, Elite2600_3000Policy,
    Elite3000OpponentA, Elite3000OpponentB, Elite3000OpponentC
};
use rayon::prelude::*;
use std::time::Instant;

pub struct ChampionshipMatchupResult {
    pub name: &'static str,
    pub tier_category: &'static str,
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

pub fn run_championship_matchup<OppFactory, Opp>(
    opp_factory: OppFactory,
    name: &'static str,
    tier_category: &'static str,
    seeds: &[u64],
) -> ChampionshipMatchupResult
where
    OppFactory: Fn() -> Opp + Sync + Send,
    Opp: Policy + 'static,
{
    // Seat 0: Hero (EXP208), Seat 1: Opponent
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

    // Seat 0: Opponent, Seat 1: Hero (EXP208)
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

    ChampionshipMatchupResult {
        name,
        tier_category,
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
    println!("     EXP211 — 100,000-MATCH GRAND CHAMPIONSHIP PRE-UPLOAD CERTIFICATION SUITE                                            ");
    println!("=========================================================================================================================");

    let t0 = Instant::now();

    // 10 Opponents x 5,000 seeds x 2 seats = 100,000 total matches on fresh seeds 1,300,000..1,350,000
    let s01_seeds: Vec<u64> = (1300000..1305000).collect();
    let s02_seeds: Vec<u64> = (1305000..1310000).collect();
    let s03_seeds: Vec<u64> = (1310000..1315000).collect();
    let s04_seeds: Vec<u64> = (1315000..1320000).collect();
    let s05_seeds: Vec<u64> = (1320000..1325000).collect();
    let s06_seeds: Vec<u64> = (1325000..1330000).collect();
    let s07_seeds: Vec<u64> = (1330000..1335000).collect();
    let s08_seeds: Vec<u64> = (1335000..1340000).collect();
    let s09_seeds: Vec<u64> = (1340000..1345000).collect();
    let s10_seeds: Vec<u64> = (1345000..1350000).collect();

    println!("\n--- [PART 1: HISTORICAL & FOUNDATIONAL BENCHMARKS (40,000 MATCHES)] ---");
    println!("[1/10] Matchup 1: EXP208 Champion vs AdaptiveTerminal (Control Chassis, 1400-1800+)...");
    let r1 = run_championship_matchup(AdaptiveTerminalPolicy::new, "AdaptiveTerminal", "Control Chassis", &s01_seeds);

    println!("[2/10] Matchup 2: EXP208 Champion vs D.1 Policy (Grandmaster Baseline, 1200-1400)...");
    let r2 = run_championship_matchup(D1Policy::new, "D.1 Grandmaster", "1200–1400 Elo", &s02_seeds);

    println!("[3/10] Matchup 3: EXP208 Champion vs V4.1 Production Classic (900-1000)...");
    let r3 = run_championship_matchup(V41Policy::new, "V4.1 Production", "900–1000 Elo", &s03_seeds);

    println!("[4/10] Matchup 4: EXP208 Champion vs EXP205 Frontier (Immediate Predecessor)...");
    let r4 = run_championship_matchup(EXP205FrontierPolicy::new, "EXP205 Frontier", "Prior Champion", &s04_seeds);

    println!("\n--- [PART 2: NEURAL BC & INTERMEDIATE ELITE LADDER (20,000 MATCHES)] ---");
    println!("[5/10] Matchup 5: EXP208 Champion vs EXP204 Elite BC Network...");
    let r5 = run_championship_matchup(EXP204EliteBCPolicy::new, "EXP204 Elite BC", "Neural BC Policy", &s05_seeds);

    println!("[6/10] Matchup 6: EXP208 Champion vs Agro-Livestock Scaler (2200–2600 Elo)...");
    let r6 = run_championship_matchup(Elite2200_2600Policy::new, "Agro-Livestock GM", "2200–2600 Elo", &s06_seeds);

    println!("\n--- [PART 3: TOP-LADDER 2600–3000+ APEX OPPONENTS (40,000 MATCHES)] ---");
    println!("[7/10] Matchup 7: EXP208 Champion vs Melon Grandmaster (2600–3000 Elo)...");
    let r7 = run_championship_matchup(Elite2600_3000Policy::new, "Melon Grandmaster", "2600–3000 Elo", &s07_seeds);

    println!("[8/10] Matchup 8: EXP208 Champion vs 3000+ Apex Opponent A (Replay 91278544, Peak $155,777)...");
    let r8 = run_championship_matchup(Elite3000OpponentA::new, "Apex Opponent A", "3000+ Replay $155k", &s08_seeds);

    println!("[9/10] Matchup 9: EXP208 Champion vs 3000+ Apex Opponent B (Replay 91282058, Peak $129,852)...");
    let r9 = run_championship_matchup(Elite3000OpponentB::new, "Apex Opponent B", "3000+ Replay $129k", &s09_seeds);

    println!("[10/10] Matchup 10: EXP208 Champion vs 3000+ Apex Opponent C (Replay 91300882, Peak $128,990)...");
    let r10 = run_championship_matchup(Elite3000OpponentC::new, "Apex Opponent C", "3000+ Replay $128k", &s10_seeds);

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nAll 100,000 Grand Championship Matches Completed in {:.2}s ({:.1} matches/sec)\n", elapsed, 100000.0 / elapsed);

    println!("=========================================================================================================================");
    println!("                              EXP211 100,000-MATCH GRAND CHAMPIONSHIP SCORECARD                                          ");
    println!("=========================================================================================================================");
    println!("{:<20} | {:<18} | {:<24} | {:<12} | {:<12} | {:<12} | {:<12}",
        "Opponent Matchup", "Tier / Category", "Win / Tie / Loss", "Hero Mean", "Opp Mean", "Net Delta", "Worst 5% Floor");
    println!("-------------------------------------------------------------------------------------------------------------------------");

    let mut total_hero_wins = 0;
    let mut total_opp_wins = 0;
    let mut total_ties = 0;
    let mut total_matches = 0;

    for r in [&r1, &r2, &r3, &r4, &r5, &r6, &r7, &r8, &r9, &r10] {
        let wr = (r.hero_wins as f64 / r.total as f64) * 100.0;
        let tr = (r.ties as f64 / r.total as f64) * 100.0;
        let lr = (r.opp_wins as f64 / r.total as f64) * 100.0;
        let delta = r.hero_mean - r.opp_mean;

        total_hero_wins += r.hero_wins;
        total_opp_wins += r.opp_wins;
        total_ties += r.ties;
        total_matches += r.total;

        println!("{:<20} | {:<18} | {:>4.1}% / {:>3.1}% / {:>4.1}% | ${:<11.1} | ${:<11.1} | {:>+11.1} | ${:<11.1}",
            r.name, r.tier_category, wr, tr, lr, r.hero_mean, r.opp_mean, delta, r.hero_worst_5pct);
    }
    println!("-------------------------------------------------------------------------------------------------------------------------");
    let combined_wr = (total_hero_wins as f64 / total_matches as f64) * 100.0;
    let combined_lr = (total_opp_wins as f64 / total_matches as f64) * 100.0;
    let combined_tr = (total_ties as f64 / total_matches as f64) * 100.0;
    println!("GRAND CHAMPIONSHIP TOTAL (100,000 MATCHES): {:>4.1}% Wins ({}) / {:>3.1}% Ties / {:>4.1}% Losses ({})",
        combined_wr, total_hero_wins, combined_tr, combined_lr, total_opp_wins);
    println!("=========================================================================================================================");
}

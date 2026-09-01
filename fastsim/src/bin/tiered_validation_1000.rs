//! 1,000-Match Multi-Opponent Tiered Tournament across Low, Mid, and High populations.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy,
    EXP208ChampionPolicy,
    AdaptiveTerminalPolicy,
    V41Policy,
    AgroHybridPolicy,
    EXP192VerifiedSheepPolicy,
    EXP186RescuePolicy,
    EXP194OpponentPolicy,
    StarterCarrotPolicy,
};
use rayon::prelude::*;
use std::time::Instant;

fn run_sub_tournament<F>(name: &str, opp_factory: F, seeds: &[u64]) -> (f64, f64, usize, usize, usize)
where
    F: Fn() -> Box<dyn Policy> + Sync + Send,
{
    let results: Vec<(f64, f64)> = seeds.par_iter().flat_map(|&seed| {
        // Seat 0: Hero, Seat 1: Opponent
        let mut st0 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        let hero0 = EXP208ChampionPolicy::new();
        let opp0 = opp_factory();
        while !st0.done {
            let a0 = hero0.act(&st0, 0);
            let a1 = opp0.act(&st0, 1);
            step_game(&mut st0, &[a0, a1]);
        }
        let res0 = (st0.farms[0].money, st0.farms[1].money);

        // Seat 0: Opponent, Seat 1: Hero
        let mut st1 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        let opp1 = opp_factory();
        let hero1 = EXP208ChampionPolicy::new();
        while !st1.done {
            let a0 = opp1.act(&st1, 0);
            let a1 = hero1.act(&st1, 1);
            step_game(&mut st1, &[a0, a1]);
        }
        let res1 = (st1.farms[1].money, st1.farms[0].money);

        vec![res0, res1]
    }).collect();

    let mut wins = 0;
    let mut losses = 0;
    let mut ties = 0;
    let mut h_tot = 0.0;
    let mut o_tot = 0.0;

    for &(h, o) in &results {
        h_tot += h;
        o_tot += o;
        if h > o {
            wins += 1;
        } else if h < o {
            losses += 1;
        } else {
            ties += 1;
        }
    }

    let n = results.len() as f64;
    (h_tot / n, o_tot / n, wins, losses, ties)
}

fn main() {
    println!("=========================================================================================");
    println!("     1,000-MATCH COMPREHENSIVE MULTI-TIER POPULATION VALIDATION                          ");
    println!("=========================================================================================");

    let t0 = Instant::now();

    // 100 seeds x 2 seats = 200 matches per opponent class
    // 5 opponent classes = 1,000 matches total
    let seeds: Vec<u64> = (2000000..2000100).collect();

    println!("\n[Tier 1] Low / Starter Population (StarterCarrot, 200 matches):");
    let (h1, o1, w1, l1, t1) = run_sub_tournament("StarterCarrot", || Box::new(StarterCarrotPolicy), &seeds);
    println!("  Hero: ${:.0} vs Opp: ${:.0} | Margin: {:+.0} | WinRate: {:.1}% ({}W/{}L/{}T)",
        h1, o1, h1 - o1, (w1 as f64 + 0.5 * t1 as f64) / (w1 + l1 + t1) as f64 * 100.0, w1, l1, t1);

    println!("\n[Tier 2] Aggressive Livestock Engine (EXP192 Verified Sheep, 200 matches):");
    let (h2, o2, w2, l2, t2) = run_sub_tournament("EXP192Sheep", || Box::new(EXP192VerifiedSheepPolicy::new()), &seeds);
    println!("  Hero: ${:.0} vs Opp: ${:.0} | Margin: {:+.0} | WinRate: {:.1}% ({}W/{}L/{}T)",
        h2, o2, h2 - o2, (w2 as f64 + 0.5 * t2 as f64) / (w2 + l2 + t2) as f64 * 100.0, w2, l2, t2);

    println!("\n[Tier 3] Mid-Elo Ladder Baseline (AdaptiveBaseline, 200 matches):");
    let (h3, o3, w3, l3, t3) = run_sub_tournament("Adaptive", || Box::new(AdaptiveTerminalPolicy::new()), &seeds);
    println!("  Hero: ${:.0} vs Opp: ${:.0} | Margin: {:+.0} | WinRate: {:.1}% ({}W/{}L/{}T)",
        h3, o3, h3 - o3, (w3 as f64 + 0.5 * t3 as f64) / (w3 + l3 + t3) as f64 * 100.0, w3, l3, t3);

    println!("\n[Tier 4] Elite Ladder Benchmark (V4.1 Multi-Expert, ~1480 Elo, 200 matches):");
    let (h4, o4, w4, l4, t4) = run_sub_tournament("V41", || Box::new(V41Policy::new()), &seeds);
    println!("  Hero: ${:.0} vs Opp: ${:.0} | Margin: {:+.0} | WinRate: {:.1}% ({}W/{}L/{}T)",
        h4, o4, h4 - o4, (w4 as f64 + 0.5 * t4 as f64) / (w4 + l4 + t4) as f64 * 100.0, w4, l4, t4);

    println!("\n[Tier 5] Adversarial Frontier (EXP194 Opponent Model, 200 matches):");
    let (h5, o5, w5, l5, t5) = run_sub_tournament("EXP194Adversarial", || Box::new(EXP194OpponentPolicy::new()), &seeds);
    println!("  Hero: ${:.0} vs Opp: ${:.0} | Margin: {:+.0} | WinRate: {:.1}% ({}W/{}L/{}T)",
        h5, o5, h5 - o5, (w5 as f64 + 0.5 * t5 as f64) / (w5 + l5 + t5) as f64 * 100.0, w5, l5, t5);

    let tot_wins = w1 + w2 + w3 + w4 + w5;
    let tot_losses = l1 + l2 + l3 + l4 + l5;
    let tot_ties = t1 + t2 + t3 + t4 + t5;
    let tot_matches = tot_wins + tot_losses + tot_ties;
    let overall_wr = (tot_wins as f64 + 0.5 * tot_ties as f64) / tot_matches as f64 * 100.0;
    let mean_hero = (h1 + h2 + h3 + h4 + h5) / 5.0;
    let mean_opp = (o1 + o2 + o3 + o4 + o5) / 5.0;
    let elapsed = t0.elapsed().as_secs_f64();

    println!("\n=========================================================================================");
    println!("     1,000-MATCH POPULATION TOURNAMENT SUMMARY                                           ");
    println!("=========================================================================================");
    println!("Total Games  : {} matches completed in {:.2}s ({:.1} matches/sec)", tot_matches, elapsed, tot_matches as f64 / elapsed);
    println!("Overall Win% : {:.1}% ({}W / {}L / {}T)", overall_wr, tot_wins, tot_losses, tot_ties);
    println!("Hero Mean    : ${:.0}", mean_hero);
    println!("Opp Mean     : ${:.0}", mean_opp);
    println!("Net Margin   : {:+.0}", mean_hero - mean_opp);
    println!("=========================================================================================");
}

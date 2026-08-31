//! Fast 200-Match Integrity Smoke Test for EXP208 Champion vs Adaptive Baseline.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy, EXP208ChampionPolicy};
use rayon::prelude::*;
use std::time::Instant;

fn main() {
    println!("=========================================================================================");
    println!("     EXP208 — 200-MATCH INTEGRITY SMOKE TEST VS ADAPTIVE BASELINE                        ");
    println!("=========================================================================================");

    let t0 = Instant::now();
    let seeds: Vec<u64> = (1500000..1500100).collect(); // 100 seeds x 2 seats = 200 matches

    // Seat 0: Hero (EXP208), Seat 1: Adaptive
    let s0: Vec<(f64, f64)> = seeds.par_iter().map(|&seed| {
        let hero = EXP208ChampionPolicy::new();
        let opp = AdaptiveTerminalPolicy::new();
        let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !st.done {
            let a0 = hero.act(&st, 0);
            let a1 = opp.act(&st, 1);
            step_game(&mut st, &[a0, a1]);
        }
        (st.farms[0].money, st.farms[1].money)
    }).collect();

    // Seat 0: Adaptive, Seat 1: Hero (EXP208)
    let s1: Vec<(f64, f64)> = seeds.par_iter().map(|&seed| {
        let opp = AdaptiveTerminalPolicy::new();
        let hero = EXP208ChampionPolicy::new();
        let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !st.done {
            let a0 = opp.act(&st, 0);
            let a1 = hero.act(&st, 1);
            step_game(&mut st, &[a0, a1]);
        }
        (st.farms[1].money, st.farms[0].money)
    }).collect();

    let mut hero_wins = 0;
    let mut opp_wins = 0;
    let mut ties = 0;
    let mut h_tot = 0.0;
    let mut o_tot = 0.0;

    for &(h, o) in s0.iter().chain(s1.iter()) {
        h_tot += h;
        o_tot += o;
        if h > o + 1.0 { hero_wins += 1; }
        else if o > h + 1.0 { opp_wins += 1; }
        else { ties += 1; }
    }

    let n = (seeds.len() * 2) as f64;
    let wr = (hero_wins as f64 / n) * 100.0;
    let lr = (opp_wins as f64 / n) * 100.0;
    let tr = (ties as f64 / n) * 100.0;
    let delta = (h_tot - o_tot) / n;

    let elapsed = t0.elapsed().as_secs_f64();
    println!("Completed 200 matches in {:.2}s", elapsed);
    println!("Scorecard: {:>4.1}% Wins ({}) / {:>3.1}% Ties ({}) / {:>4.1}% Losses ({})", wr, hero_wins, tr, ties, lr, opp_wins);
    println!("Hero Mean: ${:.1} | Opp Mean: ${:.1} | Net Delta: {:>+.1}", h_tot / n, o_tot / n, delta);
    println!("=========================================================================================");
}

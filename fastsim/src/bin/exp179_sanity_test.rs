//! EXP179 — 200-Match Sanity Test for Hierarchical BC Policy vs Adaptive Control.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{AdaptiveTerminalPolicy, HierarchicalBCPolicy, Policy};
use rayon::prelude::*;
use std::time::Instant;

fn main() {
    println!("================================================================================");
    println!("EXP179 — 200-MATCH SANITY TEST: HIERARCHICAL BC POLICY (MACRO + WORKER LAYERS)");
    println!("================================================================================");

    let hero = HierarchicalBCPolicy::new();
    let control = AdaptiveTerminalPolicy::new();

    let seeds: Vec<u64> = (1000..1100).collect(); // 100 seeds x 2 seats = 200 matches

    let mut tasks = Vec::new();
    for &seed in &seeds {
        tasks.push((seed, 0));
        tasks.push((seed, 1));
    }

    println!("Running {} paired sanity matches...", tasks.len());
    let t0 = Instant::now();

    let results: Vec<(f64, f64, [f64; 6])> = tasks.into_par_iter().map(|(seed, seat)| {
        let opp_seat = 1 - seat;
        let mut state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        let mut day_cash = [0.0; 6];
        let check_days = [1, 4, 7, 11, 15, 29];

        while !state.done && state.step < 720 {
            let day = state.day;
            let cash = state.farms[seat].money;
            for (i, &d) in check_days.iter().enumerate() {
                if day == d && state.hour == 0 {
                    day_cash[i] = cash;
                }
            }

            let a_hero = hero.act(&state, seat);
            let a_opp = control.act(&state, opp_seat);
            let actions = if seat == 0 { [a_hero, a_opp] } else { [a_opp, a_hero] };
            step_game(&mut state, &actions);
        }
        day_cash[5] = state.farms[seat].money;

        (state.farms[seat].money, state.farms[opp_seat].money, day_cash)
    }).collect();

    let elapsed = t0.elapsed().as_secs_f64();
    let total = results.len();
    let mut wins = 0;
    let mut ties = 0;
    let mut sum_hero = 0.0;
    let mut sum_ctrl = 0.0;
    let mut avg_cash = [0.0; 6];

    for (h, c, dc) in &results {
        sum_hero += h;
        sum_ctrl += c;
        for i in 0..6 { avg_cash[i] += dc[i]; }
        if *h > *c + 1.0 { wins += 1; }
        else if (*h - *c).abs() <= 1.0 { ties += 1; }
    }

    for i in 0..6 { avg_cash[i] /= total as f64; }

    let mean_hero = sum_hero / total as f64;
    let mean_ctrl = sum_ctrl / total as f64;
    let wr = (wins as f64 / total as f64) * 100.0;

    println!("\n>>> 200-MATCH SANITY RESULTS:");
    println!("    Matches: {} in {:.2}s ({:.1} eps/s)", total, elapsed, total as f64 / elapsed);
    println!("    Win Rate vs AdaptiveTerminal: {:4.1}% (Ties: {:4.1}%)", wr, (ties as f64 / total as f64) * 100.0);
    println!("    Mean Hero Reward: ${:7.1} vs Ctrl: ${:7.1} | Delta: {:+6.1}", mean_hero, mean_ctrl, mean_hero - mean_ctrl);
    println!("    Hero Cash Curve : D1=${:.0}, D4=${:.0}, D7=${:.0}, D11=${:.0}, D15=${:.0}, D30=${:.0}",
        avg_cash[0], avg_cash[1], avg_cash[2], avg_cash[3], avg_cash[4], avg_cash[5]
    );
}

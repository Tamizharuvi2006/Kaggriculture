//! EXP200.5 — FastSim Component Profiling & Bottleneck Identification.
//! Measures exact microsecond breakdown across environment stepping, policy inference, state cloning, Rayon overhead, and branching.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy, D1Policy};
use rayon::prelude::*;
use std::time::Instant;

fn main() {
    println!("=========================================================================================");
    println!("     EXP200.5 — FASTSIM CPU COMPONENT PROFILING & BOTTLENECK ANALYSIS                    ");
    println!("=========================================================================================");

    let n_matches = 1000;
    let seeds: Vec<u64> = (100000..100000 + n_matches as u64).collect();

    // 1. Measure State Cloning / Memory Allocation
    let t_clone_start = Instant::now();
    let mut initial_states = Vec::with_capacity(n_matches);
    for &s in &seeds {
        initial_states.push(GameState::new(s, 10, 3000.0, 720, 24, 100));
    }
    let init_time = t_clone_start.elapsed().as_secs_f64();

    let t_deep_clone = Instant::now();
    let cloned_states: Vec<GameState> = initial_states.iter().map(|st| st.clone()).collect();
    let clone_time = t_deep_clone.elapsed().as_secs_f64();

    // 2. Measure Component Breakdown in Single-Threaded Step Execution
    let hero = AdaptiveTerminalPolicy::new();
    let opp = D1Policy::new();

    let mut total_step_game_time = 0.0;
    let mut total_hero_act_time = 0.0;
    let mut total_opp_act_time = 0.0;
    let mut total_cf_branch_time = 0.0;
    let mut total_steps_executed = 0;

    let t_seq_start = Instant::now();
    for st_orig in cloned_states.iter().take(100) {
        let mut st = st_orig.clone();

        while !st.done {
            let t_hero = Instant::now();
            let a0 = hero.act(&st, 0);
            total_hero_act_time += t_hero.elapsed().as_secs_f64();

            let t_opp = Instant::now();
            let a1 = opp.act(&st, 1);
            total_opp_act_time += t_opp.elapsed().as_secs_f64();

            // Simulate counterfactual branch creation at critical milestones
            if st.day == 8 && st.hour == 4 {
                let t_branch = Instant::now();
                let mut cf_st = st.clone();
                let cf_a0 = hero.act(&cf_st, 0);
                let cf_a1 = opp.act(&cf_st, 1);
                step_game(&mut cf_st, &[cf_a0, cf_a1]);
                total_cf_branch_time += t_branch.elapsed().as_secs_f64();
            }

            let t_step = Instant::now();
            step_game(&mut st, &[a0, a1]);
            total_step_game_time += t_step.elapsed().as_secs_f64();

            total_steps_executed += 1;
        }
    }
    let total_seq_time = t_seq_start.elapsed().as_secs_f64();

    // 3. Measure Multi-Threaded Rayon Scaling & Scheduling Overhead
    let t_par_start = Instant::now();
    let par_results: Vec<(f64, f64)> = seeds.par_iter().map(|&s| {
        let mut st = GameState::new(s, 10, 3000.0, 720, 24, 100);
        let p0 = AdaptiveTerminalPolicy::new();
        let p1 = D1Policy::new();
        while !st.done {
            let a0 = p0.act(&st, 0);
            let a1 = p1.act(&st, 1);
            step_game(&mut st, &[a0, a1]);
        }
        (st.farms[0].money, st.farms[1].money)
    }).collect();
    let total_par_time = t_par_start.elapsed().as_secs_f64();

    let seq_extrapolated_time = (total_seq_time / 100.0) * n_matches as f64;
    let speedup = seq_extrapolated_time / total_par_time;

    println!("=========================================================================================");
    println!("                           FASTSIM CPU PROFILING BREAKDOWN                               ");
    println!("=========================================================================================");
    println!("Total Matches Profiled (Sequential Sample): 100 matches ({} steps)", total_steps_executed);
    println!("Total Sequential Simulation Time          : {:.4}s", total_seq_time);
    println!("-----------------------------------------------------------------------------------------");
    let pct_hero = (total_hero_act_time / total_seq_time) * 100.0;
    let pct_opp = (total_opp_act_time / total_seq_time) * 100.0;
    let pct_step = (total_step_game_time / total_seq_time) * 100.0;
    let pct_branch = (total_cf_branch_time / total_seq_time) * 100.0;
    let pct_other = (100.0 - (pct_hero + pct_opp + pct_step + pct_branch)).max(0.0);

    println!("1. Environment Step (`step_game`)        : {:>6.4}s ({:>5.1}%) | {:>6.2} µs/step",
        total_step_game_time, pct_step, (total_step_game_time / total_steps_executed as f64) * 1e6);
    println!("2. Hero Policy (`AdaptiveTerminal::act`)  : {:>6.4}s ({:>5.1}%) | {:>6.2} µs/step",
        total_hero_act_time, pct_hero, (total_hero_act_time / total_steps_executed as f64) * 1e6);
    println!("3. Opponent Policy (`D1::act`)            : {:>6.4}s ({:>5.1}%) | {:>6.2} µs/step",
        total_opp_act_time, pct_opp, (total_opp_act_time / total_steps_executed as f64) * 1e6);
    println!("4. Counterfactual Cloning & Branching     : {:>6.4}s ({:>5.1}%) | {:>6.2} µs/branch",
        total_cf_branch_time, pct_branch, (total_cf_branch_time / 100.0) * 1e6);
    println!("5. Loop Overhead & State Management       : {:>6.4}s ({:>5.1}%)",
        (total_seq_time - (total_step_game_time + total_hero_act_time + total_opp_act_time + total_cf_branch_time)), pct_other);
    println!("-----------------------------------------------------------------------------------------");
    println!("Parallel Rayon Execution ({} matches) : {:.3}s ({:.1} matches/sec)",
        n_matches, total_par_time, n_matches as f64 / total_par_time);
    println!("Multi-Core Parallel Speedup (12 threads)  : {:.2}x scaling efficiency", speedup);
    println!("Single State Deep Clone Overhead          : {:>6.2} µs/clone", (clone_time / n_matches as f64) * 1e6);
    println!("=========================================================================================");
}

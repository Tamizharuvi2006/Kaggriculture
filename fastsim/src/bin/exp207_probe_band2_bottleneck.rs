//! EXP207 — Forensic Probe on 2200–2600 Agro-Livestock Bottleneck.
//! Tracks step-by-step economic divergence between EXP205 and Band 2 opponent across 1,000 matches.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, EXP205FrontierPolicy, Elite2200_2600Policy};
use fastsim::farm::Tile;
use rayon::prelude::*;

pub struct TrajectoryStep {
    pub step: usize,
    pub day: usize,
    pub hero_money: f64,
    pub opp_money: f64,
    pub hero_cows: f64,
    pub opp_cows: f64,
    pub hero_sheep: f64,
    pub opp_sheep: f64,
    pub hero_workers: f64,
    pub opp_workers: f64,
}

fn main() {
    println!("=========================================================================================");
    println!("     EXP207 — FORENSIC PROBE: 2200–2600 AGRO-LIVESTOCK BOTTLENECK (1,000 MATCHES)        ");
    println!("=========================================================================================");

    let seeds: Vec<u64> = (950000..951000).collect();
    let checkpoints = [0, 50, 96, 144, 168, 192, 240, 288, 360, 480, 719];

    let all_traces: Vec<Vec<TrajectoryStep>> = seeds.par_iter().map(|&seed| {
        let hero = EXP205FrontierPolicy::new();
        let opp = Elite2200_2600Policy::new();
        let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        let mut trace = Vec::new();

        while !st.done {
            let step = st.step;
            if checkpoints.contains(&step) {
                let mut h_cows = 0.0;
                let mut h_sheep = 0.0;
                for row in &st.farms[0].tiles {
                    for t in row {
                        if let Tile::Animal(a) = t {
                            if a.animal == fastsim::farm::Animal::Cow { h_cows += 1.0; }
                            if a.animal == fastsim::farm::Animal::Sheep { h_sheep += 1.0; }
                        }
                    }
                }
                let mut o_cows = 0.0;
                let mut o_sheep = 0.0;
                for row in &st.farms[1].tiles {
                    for t in row {
                        if let Tile::Animal(a) = t {
                            if a.animal == fastsim::farm::Animal::Cow { o_cows += 1.0; }
                            if a.animal == fastsim::farm::Animal::Sheep { o_sheep += 1.0; }
                        }
                    }
                }

                trace.push(TrajectoryStep {
                    step,
                    day: st.day,
                    hero_money: st.farms[0].money,
                    opp_money: st.farms[1].money,
                    hero_cows: h_cows,
                    opp_cows: o_cows,
                    hero_sheep: h_sheep,
                    opp_sheep: o_sheep,
                    hero_workers: st.farms[0].hands.len() as f64,
                    opp_workers: st.farms[1].hands.len() as f64,
                });
            }

            let a0 = hero.act(&st, 0);
            let a1 = opp.act(&st, 1);
            step_game(&mut st, &[a0, a1]);
        }
        trace
    }).collect();

    println!("{:<14} | {:<8} | {:<15} | {:<15} | {:<15} | {:<15} | {:<15}",
        "Checkpoint", "Day", "Hero Cash ($)", "Opp Cash ($)", "Net Cash Δ", "Hero/Opp Cows", "Hero/Opp Sheep");
    println!("-------------------------------------------------------------------------------------------------------------------------");

    for (idx, &step) in checkpoints.iter().enumerate() {
        let mut h_m = 0.0;
        let mut o_m = 0.0;
        let mut h_c = 0.0;
        let mut o_c = 0.0;
        let mut h_s = 0.0;
        let mut o_s = 0.0;

        for t in &all_traces {
            if idx < t.len() {
                h_m += t[idx].hero_money;
                o_m += t[idx].opp_money;
                h_c += t[idx].hero_cows;
                o_c += t[idx].opp_cows;
                h_s += t[idx].hero_sheep;
                o_s += t[idx].opp_sheep;
            }
        }
        let n = all_traces.len() as f64;
        let d = step / 24;
        let delta_m = (h_m - o_m) / n;

        println!("Step {:<9} | Day {:<4} | ${:<14.1} | ${:<14.1} | {:>+14.1} | {:<4.1} / {:<4.1} cows | {:<4.1} / {:<4.1} sheep",
            step, d, h_m / n, o_m / n, delta_m, h_c / n, o_c / n, h_s / n, o_s / n);
    }
    println!("=========================================================================================================================");
}

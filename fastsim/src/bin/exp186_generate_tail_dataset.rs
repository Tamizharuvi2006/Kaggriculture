//! EXP186 — Tail-Stall Dataset Generator.
//! Identifies exact failing trajectories under AdaptiveTerminal and records state signatures + rescue counterfactuals.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};
use fastsim::market::{Product, MarketOrder};
use fastsim::farm::{Crop, Animal, Tile};
use rayon::prelude::*;
use std::fs::File;
use std::io::Write;
use std::time::Instant;

#[derive(Clone, Debug)]
pub struct TailStateSample {
    pub seed: u64,
    pub step: usize,
    pub day: usize,
    pub hour: usize,
    pub money: f64,
    pub unlocked_quads: usize,
    pub num_hands: usize,
    pub num_plants: usize,
    pub num_cows: usize,
    pub shed_straw: i64,
    pub shed_milk: i64,
    pub shed_wheat: i64,
    pub p_straw: f64,
    pub p_milk: f64,
    pub p_melon: f64,
    pub opp_money: f64,
    pub opp_quads: usize,
    pub final_baseline_reward: f64,
    pub is_stall: bool,
    pub rescue_wheat_reward: f64,
    pub rescue_hire1_reward: f64,
    pub rescue_hire2_reward: f64,
}

fn main() {
    println!("================================================================================");
    println!("EXP186 — GENERATING BINARY TAIL-STALL DATASET (5,000 SEEDS x CHECKPOINTS)");
    println!("================================================================================");

    let base_policy = AdaptiveTerminalPolicy::new();
    let opp_policy = AdaptiveTerminalPolicy::new();

    let num_seeds = 5000;
    let seeds: Vec<u64> = (1000..(1000 + num_seeds as u64)).collect();

    // Sample during the critical vulnerability window: Days 0, 1, 2, 3, 4, 5, 6, 7
    let checkpoint_steps: Vec<usize> = vec![0, 24, 48, 72, 96, 120, 144, 168];

    println!("Simulating {} full episodes to classify tail stalls (< $50,000 finish)...", num_seeds);
    let t0 = Instant::now();

    let all_seed_samples: Vec<Vec<TailStateSample>> = seeds.into_par_iter().map(|seed| {
        let mut samples = Vec::new();

        // 1. Run full baseline game to determine if this seed collapses
        let mut base_state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        let mut checkpoints_states: Vec<(usize, GameState)> = Vec::new();

        while !base_state.done {
            if checkpoint_steps.contains(&base_state.step) {
                checkpoints_states.push((base_state.step, base_state.clone()));
            }
            let a0 = base_policy.act(&base_state, 0);
            let a1 = opp_policy.act(&base_state, 1);
            step_game(&mut base_state, &[a0, a1]);
        }

        let final_reward = base_state.farms[0].money;
        let is_stall = final_reward < 50000.0;

        // 2. For each checkpoint, extract state features and run emergency rescue counterfactuals
        for (step, st) in checkpoints_states {
            let farm = &st.farms[0];
            let priv_farm = &st.privates[0];
            let opp_farm = &st.farms[1];

            let mut num_plants = 0;
            let mut num_cows = 0;
            for row in &farm.tiles {
                for tile in row {
                    match tile {
                        Tile::Plant(_) => num_plants += 1,
                        Tile::Animal(a) if a.animal == Animal::Cow => num_cows += 1,
                        _ => {}
                    }
                }
            }

            let shed_straw = *priv_farm.shed.get("STRAWBERRY").unwrap_or(&0);
            let shed_milk = *priv_farm.shed.get("MILK").unwrap_or(&0);
            let shed_wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0);

            let p_straw = *st.market.prices.get(&Product::Strawberry).unwrap_or(&120) as f64;
            let p_milk = *st.market.prices.get(&Product::Milk).unwrap_or(&160) as f64;
            let p_melon = *st.market.prices.get(&Product::Melon).unwrap_or(&100) as f64;

            let base_act = base_policy.act(&st, 0);
            let opp_act = opp_policy.act(&st, 1);

            // Rescue 1: BUY_WHEAT_4 (Feed buffer)
            let mut wheat_state = st.clone();
            let mut wheat_act = base_act.clone();
            if farm.money >= 40.0 {
                wheat_act.market.push(MarketOrder::BuySeed(Crop::Wheat, 4));
            }
            step_game(&mut wheat_state, &[wheat_act, opp_act.clone()]);
            while !wheat_state.done {
                let a0 = base_policy.act(&wheat_state, 0);
                let a1 = opp_policy.act(&wheat_state, 1);
                step_game(&mut wheat_state, &[a0, a1]);
            }
            let rescue_wheat_reward = wheat_state.farms[0].money;

            // Rescue 2: HIRE_1 (Labor buffer)
            let mut hire1_state = st.clone();
            let mut hire1_act = base_act.clone();
            if farm.money >= 50.0 && farm.hands.len() < 16 {
                hire1_act.market.push(MarketOrder::Hire);
            }
            step_game(&mut hire1_state, &[hire1_act, opp_act.clone()]);
            while !hire1_state.done {
                let a0 = base_policy.act(&hire1_state, 0);
                let a1 = opp_policy.act(&hire1_state, 1);
                step_game(&mut hire1_state, &[a0, a1]);
            }
            let rescue_hire1_reward = hire1_state.farms[0].money;

            // Rescue 3: HIRE_2 (Labor buffer)
            let mut hire2_state = st.clone();
            let mut hire2_act = base_act.clone();
            if farm.money >= 100.0 && farm.hands.len() < 15 {
                hire2_act.market.push(MarketOrder::Hire);
                hire2_act.market.push(MarketOrder::Hire);
            }
            step_game(&mut hire2_state, &[hire2_act, opp_act]);
            while !hire2_state.done {
                let a0 = base_policy.act(&hire2_state, 0);
                let a1 = opp_policy.act(&hire2_state, 1);
                step_game(&mut hire2_state, &[a0, a1]);
            }
            let rescue_hire2_reward = hire2_state.farms[0].money;

            samples.push(TailStateSample {
                seed,
                step,
                day: st.day,
                hour: st.hour,
                money: farm.money,
                unlocked_quads: farm.unlocked_quadrants.len(),
                num_hands: farm.hands.len(),
                num_plants,
                num_cows,
                shed_straw,
                shed_milk,
                shed_wheat,
                p_straw,
                p_milk,
                p_melon,
                opp_money: opp_farm.money,
                opp_quads: opp_farm.unlocked_quadrants.len(),
                final_baseline_reward: final_reward,
                is_stall,
                rescue_wheat_reward,
                rescue_hire1_reward,
                rescue_hire2_reward,
            });
        }

        samples
    }).collect();

    let flat_samples: Vec<TailStateSample> = all_seed_samples.into_iter().flatten().collect();
    let elapsed = t0.elapsed().as_secs_f64();

    println!("\nProcessed {} state snapshots across {} seeds in {:.2}s ({:.1} state-evals/sec)!",
        flat_samples.len(), num_seeds, elapsed, flat_samples.len() as f64 / elapsed);

    let total_stalls = flat_samples.iter().filter(|s| s.is_stall).count();
    println!("Total Stall States (Reward < $50k) : {} ({:.2}%)", total_stalls, (total_stalls as f64 / flat_samples.len() as f64) * 100.0);

    // Save to CSV
    let out_path = r"D:\kaggriculture\data\exp186_tail_risk_dataset.csv";
    let mut file = File::create(out_path).expect("Failed to create CSV file");

    writeln!(file, "seed,step,day,hour,money,unlocked_quads,num_hands,num_plants,num_cows,shed_straw,shed_milk,shed_wheat,p_straw,p_milk,p_melon,opp_money,opp_quads,final_baseline_reward,is_stall,rescue_wheat_reward,rescue_hire1_reward,rescue_hire2_reward").unwrap();

    for s in &flat_samples {
        writeln!(
            file,
            "{},{},{},{},{:.2},{},{},{},{},{},{},{},{:.2},{:.2},{:.2},{:.2},{},{:.2},{},{:.2},{:.2},{:.2}",
            s.seed, s.step, s.day, s.hour, s.money, s.unlocked_quads, s.num_hands, s.num_plants, s.num_cows,
            s.shed_straw, s.shed_milk, s.shed_wheat, s.p_straw, s.p_milk, s.p_melon, s.opp_money, s.opp_quads,
            s.final_baseline_reward, if s.is_stall { 1 } else { 0 }, s.rescue_wheat_reward, s.rescue_hire1_reward, s.rescue_hire2_reward
        ).unwrap();
    }

    println!("Dataset written to {}", out_path);
    println!("================================================================================");
}

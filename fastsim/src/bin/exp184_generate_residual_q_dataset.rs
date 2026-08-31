//! EXP184-A — High-Throughput Residual Q Dataset Generator on Top of AdaptiveTerminal.
//! Generates 60,000+ exact counterfactuals around the $81,000+ Grandmaster trajectory using Common Random Numbers.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};

use fastsim::market::{Product, MarketOrder};
use fastsim::farm::{Crop, Animal};
use rayon::prelude::*;
use std::fs::File;
use std::io::Write;
use std::time::Instant;

#[derive(Clone, Debug)]
pub struct ResidualSample {
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
    pub action_id: usize,
    pub action_name: &'static str,
    pub baseline_reward: f64,
    pub counterfactual_reward: f64,
    pub delta_reward: f64,
}

pub const RESIDUAL_ACTIONS: [&str; 14] = [
    "BASELINE",
    "HIRE_1",
    "HIRE_2",
    "HIRE_3",
    "BUY_SEED_MELON_6",
    "BUY_SEED_MELON_8",
    "BUY_SEED_STRAW_4",
    "BUY_SEED_STRAW_8",
    "BUY_SEED_STRAW_16",
    "BUY_SEED_WHEAT_4",
    "BUY_COW_1",
    "BUY_LAND",
    "FORCE_SELL_ALL",
    "HOLD_COMMODITIES",
];

pub fn get_intervention_orders(
    action_id: usize,
    state: &GameState,
    player_idx: usize,
    base_orders: &[MarketOrder],
) -> Option<Vec<MarketOrder>> {
    let farm = &state.farms[player_idx];
    let priv_farm = &state.privates[player_idx];
    let money = farm.money;
    let quads = farm.unlocked_quadrants.len();
    let hands = farm.hands.len();

    let mut orders = base_orders.to_vec();

    match action_id {
        0 => Some(orders), // BASELINE
        1 => { // HIRE_1
            if money >= 50.0 && hands < 16 {
                orders.push(MarketOrder::Hire);
                Some(orders)
            } else { None }
        }
        2 => { // HIRE_2
            if money >= 100.0 && hands < 15 {
                orders.push(MarketOrder::Hire);
                orders.push(MarketOrder::Hire);
                Some(orders)
            } else { None }
        }
        3 => { // HIRE_3
            if money >= 150.0 && hands < 14 {
                orders.push(MarketOrder::Hire);
                orders.push(MarketOrder::Hire);
                orders.push(MarketOrder::Hire);
                Some(orders)
            } else { None }
        }
        4 => { // BUY_SEED_MELON_6
            if money >= 480.0 {
                orders.push(MarketOrder::BuySeed(Crop::Melon, 6));
                Some(orders)
            } else { None }
        }
        5 => { // BUY_SEED_MELON_8
            if money >= 640.0 {
                orders.push(MarketOrder::BuySeed(Crop::Melon, 8));
                Some(orders)
            } else { None }
        }
        6 => { // BUY_SEED_STRAW_4
            if money >= 400.0 {
                orders.push(MarketOrder::BuySeed(Crop::Strawberry, 4));
                Some(orders)
            } else { None }
        }
        7 => { // BUY_SEED_STRAW_8
            if money >= 800.0 {
                orders.push(MarketOrder::BuySeed(Crop::Strawberry, 8));
                Some(orders)
            } else { None }
        }
        8 => { // BUY_SEED_STRAW_16
            if money >= 1600.0 {
                orders.push(MarketOrder::BuySeed(Crop::Strawberry, 16));
                Some(orders)
            } else { None }
        }
        9 => { // BUY_SEED_WHEAT_4
            if money >= 40.0 {
                orders.push(MarketOrder::BuySeed(Crop::Wheat, 4));
                Some(orders)
            } else { None }
        }
        10 => { // BUY_COW_1
            if money >= 800.0 {
                orders.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
                Some(orders)
            } else { None }
        }
        11 => { // BUY_LAND
            let cost = match quads {
                1 => 1000.0,
                2 => 2000.0,
                3 => 4000.0,
                _ => 999999.0,
            };
            if money >= cost && quads < 4 {
                orders.push(MarketOrder::BuyLand);
                Some(orders)
            } else { None }
        }
        12 => { // FORCE_SELL_ALL
            for prod in Product::ALL {
                let count = *priv_farm.shed.get(prod.name()).unwrap_or(&0);
                if count > 0 {
                    orders.push(MarketOrder::Sell(prod, count));
                }
            }
            Some(orders)
        }
        13 => { // HOLD_COMMODITIES (Filter out sell orders this step)
            orders.retain(|o| !matches!(o, MarketOrder::Sell(_, _)));
            Some(orders)
        }
        _ => None,
    }
}

fn main() {
    println!("================================================================================");
    println!("EXP184-A — GENERATING RESIDUAL Q DATASET ON ADAPTIVETERMINAL (60,000+ RUNS)");
    println!("================================================================================");

    let base_policy = AdaptiveTerminalPolicy::new();
    let opp_policy = AdaptiveTerminalPolicy::new();

    let num_seeds = 1500; // 1,500 diverse seeds
    let seeds: Vec<u64> = (1000..(1000 + num_seeds as u64)).collect();

    // Checkpoint days: Days 0, 1, 2, 3, 4, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25
    let checkpoint_steps: Vec<usize> = vec![
        0, 24, 48, 72, 96, 120, 168, 216, 264, 312, 360, 408, 456, 504, 552, 600
    ];

    let mut tasks = Vec::new();
    for &seed in &seeds {
        for &step in &checkpoint_steps {
            tasks.push((seed, step));
        }
    }

    println!("Evaluating {} (Seed x Checkpoint) pairs x 14 candidate actions...", tasks.len());
    let t0 = Instant::now();

    let all_samples: Vec<Vec<ResidualSample>> = tasks.into_par_iter().map(|(seed, interv_step)| {
        let mut samples = Vec::new();

        // 1. Roll to intervention step under AdaptiveTerminal
        let mut state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !state.done && state.step < interv_step {
            let a0 = base_policy.act(&state, 0);
            let a1 = opp_policy.act(&state, 1);
            step_game(&mut state, &[a0, a1]);
        }

        if state.done { return samples; }

        let interv_state = state.clone();

        // 2. Compute Baseline Terminal Return from this checkpoint
        let mut baseline_state = interv_state.clone();
        while !baseline_state.done {
            let a0 = base_policy.act(&baseline_state, 0);
            let a1 = opp_policy.act(&baseline_state, 1);
            step_game(&mut baseline_state, &[a0, a1]);
        }
        let baseline_reward = baseline_state.farms[0].money;

        // Snapshot state features at intervention step
        let farm = &interv_state.farms[0];
        let priv_farm = &interv_state.privates[0];
        let opp_farm = &interv_state.farms[1];

        let money = farm.money;
        let unlocked_quads = farm.unlocked_quadrants.len();
        let num_hands = farm.hands.len();
        let mut num_plants = 0;
        let mut num_cows = 0;
        for row in &farm.tiles {
            for tile in row {
                match tile {
                    fastsim::farm::Tile::Plant(_) => num_plants += 1,
                    fastsim::farm::Tile::Animal(a) if a.animal == Animal::Cow => num_cows += 1,
                    _ => {}
                }
            }
        }

        let shed_straw = *priv_farm.shed.get("STRAWBERRY").unwrap_or(&0);
        let shed_milk = *priv_farm.shed.get("MILK").unwrap_or(&0);
        let shed_wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0);

        let p_straw = *interv_state.market.prices.get(&Product::Strawberry).unwrap_or(&120) as f64;
        let p_milk = *interv_state.market.prices.get(&Product::Milk).unwrap_or(&160) as f64;
        let p_melon = *interv_state.market.prices.get(&Product::Melon).unwrap_or(&100) as f64;

        let opp_money = opp_farm.money;
        let opp_quads = opp_farm.unlocked_quadrants.len();

        let base_act = base_policy.act(&interv_state, 0);

        // 3. Evaluate each of the 14 candidate counterfactual actions
        for (action_id, &action_name) in RESIDUAL_ACTIONS.iter().enumerate() {
            if let Some(cf_orders) = get_intervention_orders(action_id, &interv_state, 0, &base_act.market) {
                let mut cf_state = interv_state.clone();
                let opp_act = opp_policy.act(&cf_state, 1);

                let mut hero_act = base_act.clone();
                hero_act.market = cf_orders;

                step_game(&mut cf_state, &[hero_act, opp_act]);

                while !cf_state.done {
                    let a0 = base_policy.act(&cf_state, 0);
                    let a1 = opp_policy.act(&cf_state, 1);
                    step_game(&mut cf_state, &[a0, a1]);
                }

                let cf_reward = cf_state.farms[0].money;
                let delta_reward = cf_reward - baseline_reward;

                samples.push(ResidualSample {
                    seed,
                    step: interv_step,
                    day: interv_state.day,
                    hour: interv_state.hour,
                    money,
                    unlocked_quads,
                    num_hands,
                    num_plants,
                    num_cows,
                    shed_straw,
                    shed_milk,
                    shed_wheat,
                    p_straw,
                    p_milk,
                    p_melon,
                    opp_money,
                    opp_quads,
                    action_id,
                    action_name,
                    baseline_reward,
                    counterfactual_reward: cf_reward,
                    delta_reward,
                });
            }
        }

        samples
    }).collect();

    let flat_samples: Vec<ResidualSample> = all_samples.into_iter().flatten().collect();
    let elapsed = t0.elapsed().as_secs_f64();

    println!("\nGenerated {} residual counterfactual samples in {:.2}s ({:.1} rollouts/sec)!",
        flat_samples.len(), elapsed, flat_samples.len() as f64 / elapsed);

    // Save to CSV
    let out_path = r"D:\kaggriculture\data\exp184_residual_q_dataset.csv";
    let mut file = File::create(out_path).expect("Failed to create CSV file");

    writeln!(file, "seed,step,day,hour,money,unlocked_quads,num_hands,num_plants,num_cows,shed_straw,shed_milk,shed_wheat,p_straw,p_milk,p_melon,opp_money,opp_quads,action_id,action_name,baseline_reward,counterfactual_reward,delta_reward").unwrap();

    let mut positive_improvements = 0;
    let mut max_gain = 0.0f64;

    for s in &flat_samples {
        if s.delta_reward > 500.0 { positive_improvements += 1; }
        if s.delta_reward > max_gain { max_gain = s.delta_reward; }

        writeln!(
            file,
            "{},{},{},{},{:.2},{},{},{},{},{},{},{},{:.2},{:.2},{:.2},{:.2},{},{},{},{:.2},{:.2},{:.2}",
            s.seed, s.step, s.day, s.hour, s.money, s.unlocked_quads, s.num_hands, s.num_plants, s.num_cows,
            s.shed_straw, s.shed_milk, s.shed_wheat, s.p_straw, s.p_milk, s.p_melon, s.opp_money, s.opp_quads,
            s.action_id, s.action_name, s.baseline_reward, s.counterfactual_reward, s.delta_reward
        ).unwrap();
    }

    println!("\nDataset written to {}", out_path);
    println!("Total Samples               : {}", flat_samples.len());
    println!("Significant Gains (> +$500) : {} ({:.1}%)", positive_improvements, (positive_improvements as f64 / flat_samples.len() as f64) * 100.0);
    println!("Max Single-Action Gain      : +${:.2}", max_gain);
    println!("================================================================================");
}


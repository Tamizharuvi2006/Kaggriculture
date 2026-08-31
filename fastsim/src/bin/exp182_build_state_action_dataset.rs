//! EXP182 — State-Action Counterfactual Value Dataset Builder.
//! Evaluates counterfactual macro economic actions on diverse Day 0-15 states to train Q(s, a) and V(s).

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{AdaptiveTerminalPolicy, TargetDispatcherPolicy, Policy};
use fastsim::market::MarketOrder;
use fastsim::farm::{Animal, Tile, Crop};
use rayon::prelude::*;
use std::fs::File;
use std::io::Write;
use std::time::Instant;

#[derive(Clone, Debug)]
pub struct CounterfactualSample {
    pub seed: u64,
    pub step: usize,
    pub day: usize,
    pub money: f64,
    pub melon_seeds: i64,
    pub wheat_seeds: i64,
    pub straw_seeds: i64,
    pub unlocked_quads: usize,
    pub num_plants: usize,
    pub num_cows: usize,
    pub num_hands: usize,
    pub action_id: usize, // 0..12
    pub terminal_return: f64,
    pub delta_vs_baseline: f64,
}

pub fn get_market_orders_for_action(action_id: usize, money: f64, unlocked_quads: usize) -> Vec<MarketOrder> {
    match action_id {
        0 => vec![], // HOLD
        1 => if money >= 50.0 { vec![MarketOrder::Hire] } else { vec![] },
        2 => if money >= 100.0 { vec![MarketOrder::Hire, MarketOrder::Hire] } else { vec![] },
        3 => if money >= 150.0 { vec![MarketOrder::Hire, MarketOrder::Hire, MarketOrder::Hire] } else { vec![] },
        4 => if money >= 480.0 { vec![MarketOrder::BuySeed(Crop::Melon, 6)] } else { vec![] },
        5 => if money >= 640.0 { vec![MarketOrder::BuySeed(Crop::Melon, 8)] } else { vec![] },
        6 => if money >= 40.0 { vec![MarketOrder::BuySeed(Crop::Wheat, 4)] } else { vec![] },
        7 => if money >= 60.0 { vec![MarketOrder::BuySeed(Crop::Wheat, 6)] } else { vec![] },
        8 => if money >= 400.0 { vec![MarketOrder::BuySeed(Crop::Strawberry, 4)] } else { vec![] },
        9 => if money >= 800.0 { vec![MarketOrder::BuySeed(Crop::Strawberry, 8)] } else { vec![] },
        10 => if money >= 800.0 { vec![MarketOrder::BuyAnimal(Animal::Cow, 1)] } else { vec![] },
        11 => if money >= 1000.0 && unlocked_quads < 4 { vec![MarketOrder::BuyLand] } else { vec![] },
        _ => vec![],
    }
}

fn main() {
    println!("================================================================================");
    println!("EXP182 — GENERATING COUNTERFACTUAL STATE-ACTION DATASET (42,000 EVALUATIONS)");
    println!("================================================================================");

    let base_policy = TargetDispatcherPolicy::new();
    let opp_policy = AdaptiveTerminalPolicy::new();

    let seeds: Vec<u64> = (1000..1500).collect(); // 500 diverse seeds
    let intervention_checkpoints = [0, 24, 72, 120, 168, 216, 264]; // Days 0, 1, 3, 5, 7, 9, 11

    let mut tasks = Vec::new();
    for &seed in &seeds {
        for &interv_step in &intervention_checkpoints {
            tasks.push((seed, interv_step));
        }
    }

    println!("Evaluating {} state checkpoints x 12 actions on 12 threads...", tasks.len());
    let t0 = Instant::now();

    let all_samples: Vec<Vec<CounterfactualSample>> = tasks.into_par_iter().map(|(seed, interv_step)| {
        let mut samples = Vec::new();

        // 1. Roll to intervention step under base policy
        let mut base_state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !base_state.done && base_state.step < interv_step {
            let a_hero = base_policy.act(&base_state, 0);
            let a_opp = opp_policy.act(&base_state, 1);
            step_game(&mut base_state, &[a_hero, a_opp]);
        }

        if base_state.done { return samples; }

        let farm = &base_state.farms[0];
        let priv_farm = &base_state.privates[0];
        let money = farm.money;
        let day = base_state.day;
        let melon_seeds = *priv_farm.seeds.get(&Crop::Melon).unwrap_or(&0);
        let wheat_seeds = *priv_farm.seeds.get(&Crop::Wheat).unwrap_or(&0);
        let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);
        let unlocked_quads = farm.unlocked_quadrants.len();
        let num_hands = farm.hands.len();

        let mut num_plants = 0;
        let mut num_cows = 0;
        for row in &farm.tiles {
            for t in row {
                if let Tile::Plant(_) = t { num_plants += 1; }
                if let Tile::Animal(a) = t { if a.animal == Animal::Cow { num_cows += 1; } }
            }
        }

        // 2. Evaluate Baseline Rollout (Action 0 = HOLD / Base)
        let mut rollout_state = base_state.clone();
        while !rollout_state.done && rollout_state.step < 720 {
            let a_hero = base_policy.act(&rollout_state, 0);
            let a_opp = opp_policy.act(&rollout_state, 1);
            step_game(&mut rollout_state, &[a_hero, a_opp]);
        }
        let baseline_return = rollout_state.farms[0].money;

        // 3. Evaluate 12 Counterfactual Actions
        for action_id in 0..12 {
            let mut cf_state = base_state.clone();
            let mut a_hero = base_policy.act(&cf_state, 0);
            let extra_orders = get_market_orders_for_action(action_id, money, unlocked_quads);
            a_hero.market.extend(extra_orders);
            let a_opp = opp_policy.act(&cf_state, 1);

            step_game(&mut cf_state, &[a_hero, a_opp]);

            // Roll remainder of game under policy
            while !cf_state.done && cf_state.step < 720 {
                let a_h = base_policy.act(&cf_state, 0);
                let a_o = opp_policy.act(&cf_state, 1);
                step_game(&mut cf_state, &[a_h, a_o]);
            }

            let cf_return = cf_state.farms[0].money;
            samples.push(CounterfactualSample {
                seed,
                step: interv_step,
                day,
                money,
                melon_seeds,
                wheat_seeds,
                straw_seeds,
                unlocked_quads,
                num_plants,
                num_cows,
                num_hands,
                action_id,
                terminal_return: cf_return,
                delta_vs_baseline: cf_return - baseline_return,
            });
        }

        samples
    }).collect();

    let flat_samples: Vec<CounterfactualSample> = all_samples.into_iter().flatten().collect();
    let elapsed = t0.elapsed().as_secs_f64();

    println!("\n>>> DATASET GENERATION COMPLETE:");
    println!("    Total Evaluated Samples: {} in {:.2}s ({:.1} cf-evals/s)", flat_samples.len(), elapsed, flat_samples.len() as f64 / elapsed);

    let out_path = "D:\\kaggriculture\\data\\exp182_q_dataset.csv";
    let mut file = File::create(out_path).expect("failed to create CSV file");
    writeln!(file, "seed,step,day,money,melon_seeds,wheat_seeds,straw_seeds,unlocked_quads,num_plants,num_cows,num_hands,action_id,terminal_return,delta_vs_baseline").unwrap();

    let mut improvements = 0;
    let mut max_gain = 0.0;

    for s in &flat_samples {
        writeln!(file, "{},{},{},{:.1},{},{},{},{},{},{},{},{},{:.1},{:.1}",
            s.seed, s.step, s.day, s.money, s.melon_seeds, s.wheat_seeds, s.straw_seeds,
            s.unlocked_quads, s.num_plants, s.num_cows, s.num_hands, s.action_id,
            s.terminal_return, s.delta_vs_baseline
        ).unwrap();

        if s.delta_vs_baseline > 500.0 {
            improvements += 1;
            if s.delta_vs_baseline > max_gain { max_gain = s.delta_vs_baseline; }
        }
    }

    println!("    Saved to: {}", out_path);
    println!("    High-Value Counterfactual Improvements (>+$500): {} ({:.1}%)", improvements, (improvements as f64 / flat_samples.len() as f64) * 100.0);
    println!("    Max Single Action Gain Discovered: +${:.1}", max_gain);
}

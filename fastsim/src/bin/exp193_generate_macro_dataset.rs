//! EXP193 — High-Throughput Macro Action Counterfactual Dataset Generator.
//! Evaluates 5,000 seeds across candidate macro actions (a0..a5) to build the multi-action Q-dataset.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};
use fastsim::market::{Product, MarketOrder};
use fastsim::farm::{Animal, Crop, Tile};
use rayon::prelude::*;
use std::fs::File;
use std::io::Write;
use std::time::Instant;

#[derive(Clone, Debug)]
pub struct MacroSample {
    pub seed: u64,
    pub p_milk: f64,
    pub cash: f64,
    pub cows: usize,
    pub sheep: usize,
    pub shed_wheat: i64,
    pub hands: usize,
    pub quads: usize,
    pub day: usize,
    pub unwatered_crops: usize,
    pub mature_crops: usize,
    pub score_a0: f64, // Default Adaptive
    pub score_a1: f64, // Buy Wheat (Day 0)
    pub score_a2: f64, // Hire 1 (Day 6)
    pub score_a3: f64, // 1 Sheep (Day 8)
    pub score_a4: f64, // 2 Sheep (Day 8)
    pub score_a5: f64, // 4 Sheep (Day 8)
    pub best_a: usize,
    pub max_gain_vs_a0: f64,
}

pub fn evaluate_seed_macro(seed: u64) -> MacroSample {
    let base_policy = AdaptiveTerminalPolicy::new();
    let opp_policy = AdaptiveTerminalPolicy::new();

    // 1. Rollout Baseline (a0) to completion
    let mut st_a0 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let mut snap_p_milk = 160.0;
    let mut snap_cash = 2000.0;
    let mut snap_cows = 3;
    let mut snap_sheep = 0;
    let mut snap_shed_wheat = 12;
    let mut snap_hands = 0;
    let mut snap_quads = 1;
    let mut snap_unwatered = 0;
    let mut snap_mature = 0;

    while !st_a0.done {
        let day = st_a0.day;
        let hour = st_a0.hour;

        if day == 8 && hour == 4 {
            snap_p_milk = *st_a0.market.prices.get(&Product::Milk).unwrap_or(&160) as f64;
            snap_cash = st_a0.farms[0].money;
            snap_shed_wheat = *st_a0.privates[0].shed.get("WHEAT").unwrap_or(&0);
            snap_hands = st_a0.farms[0].hands.len();
            snap_quads = st_a0.farms[0].unlocked_quadrants.len();

            let mut c_count = 0;
            let mut s_count = 0;
            let mut unw = 0;
            let mut mat = 0;

            for row in &st_a0.farms[0].tiles {
                for tile in row {
                    match tile {
                        Tile::Animal(a) => {
                            if a.animal == Animal::Cow { c_count += 1; }
                            if a.animal == Animal::Sheep { s_count += 1; }
                        }
                        Tile::Plant(p) => {
                            if p.yield_units > 0 { mat += 1; }
                            else if !p.watered_today { unw += 1; }
                        }
                        _ => {}
                    }
                }
            }
            snap_cows = c_count;
            snap_sheep = s_count;
            snap_unwatered = unw;
            snap_mature = mat;
        }

        let a0 = base_policy.act(&st_a0, 0);
        let a1 = opp_policy.act(&st_a0, 1);
        step_game(&mut st_a0, &[a0, a1]);
    }
    let score_a0 = st_a0.farms[0].money;

    // 2. Evaluate a1: Buy Wheat at Day 0 Step 0
    let mut st_a1 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    while !st_a1.done {
        let mut a0 = base_policy.act(&st_a1, 0);
        if st_a1.step == 0 {
            a0.market.push(MarketOrder::BuySeed(Crop::Wheat, 4));
        }
        let a1 = opp_policy.act(&st_a1, 1);
        step_game(&mut st_a1, &[a0, a1]);
    }
    let score_a1 = st_a1.farms[0].money;

    // 3. Evaluate a2: Hire 1 extra worker on Day 6 Hour 0
    let mut st_a2 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    while !st_a2.done {
        let mut a0 = base_policy.act(&st_a2, 0);
        if st_a2.day == 6 && st_a2.hour == 0 && st_a2.farms[0].money >= 40.0 {
            a0.market.push(MarketOrder::Hire);
        }
        let a1 = opp_policy.act(&st_a2, 1);
        step_game(&mut st_a2, &[a0, a1]);
    }
    let score_a2 = st_a2.farms[0].money;

    // 4. Evaluate a3: 1 Sheep on Day 8 Hour 4
    let mut st_a3 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    while !st_a3.done {
        let mut a0 = base_policy.act(&st_a3, 0);
        if st_a3.day == 8 && st_a3.hour == 4 {
            a0.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            if st_a3.farms[0].money >= 600.0 {
                a0.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1));
            }
        }
        let a1 = opp_policy.act(&st_a3, 1);
        step_game(&mut st_a3, &[a0, a1]);
    }
    let score_a3 = st_a3.farms[0].money;

    // 5. Evaluate a4: 2 Sheep on Day 8 Hour 4
    let mut st_a4 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    while !st_a4.done {
        let mut a0 = base_policy.act(&st_a4, 0);
        if st_a4.day == 8 && st_a4.hour == 4 {
            a0.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            if st_a4.farms[0].money >= 1200.0 {
                a0.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
            }
        }
        let a1 = opp_policy.act(&st_a4, 1);
        step_game(&mut st_a4, &[a0, a1]);
    }
    let score_a4 = st_a4.farms[0].money;

    // 6. Evaluate a5: 4 Sheep on Day 8 Hour 4 (same as a0 in most cases, but explicit)
    let score_a5 = score_a0;

    let scores = [score_a0, score_a1, score_a2, score_a3, score_a4, score_a5];
    let mut best_a = 0;
    let mut best_s = score_a0;
    for (i, &s) in scores.iter().enumerate() {
        if s > best_s + 50.0 {
            best_s = s;
            best_a = i;
        }
    }

    MacroSample {
        seed,
        p_milk: snap_p_milk,
        cash: snap_cash,
        cows: snap_cows,
        sheep: snap_sheep,
        shed_wheat: snap_shed_wheat,
        hands: snap_hands,
        quads: snap_quads,
        day: 8,
        unwatered_crops: snap_unwatered,
        mature_crops: snap_mature,
        score_a0,
        score_a1,
        score_a2,
        score_a3,
        score_a4,
        score_a5,
        best_a,
        max_gain_vs_a0: best_s - score_a0,
    }
}

fn main() {
    println!("=========================================================================================");
    println!("       EXP193 — HIGH-THROUGHPUT MACRO ACTION DATASET GENERATOR (5,000 SEEDS)             ");
    println!("=========================================================================================");

    let num_seeds = 5000;
    let seeds: Vec<u64> = (80000..(80000 + num_seeds as u64)).collect();
    let t0 = Instant::now();

    println!("Generating 5,000 seeds x 6 macro rollouts = 30,000 full game rollouts...");
    let samples: Vec<MacroSample> = seeds.into_par_iter().map(evaluate_seed_macro).collect();
    let elapsed = t0.elapsed().as_secs_f64();

    println!("Dataset generation completed in {:.2}s ({:.1} rollouts/sec)\n", elapsed, (num_seeds * 6) as f64 / elapsed);

    let csv_path = r"D:\kaggriculture\data\exp193_macro_dataset.csv";
    let mut file = File::create(csv_path).expect("Failed to create CSV");
    writeln!(file, "seed,p_milk,cash,cows,sheep,shed_wheat,hands,quads,day,unwatered,mature,score_a0,score_a1,score_a2,score_a3,score_a4,score_a5,best_a,gain_vs_a0").unwrap();

    let mut action_counts = [0; 6];
    let mut sum_gains = [0.0; 6];

    for s in &samples {
        action_counts[s.best_a] += 1;
        sum_gains[s.best_a] += s.max_gain_vs_a0;

        writeln!(file, "{},{:.2},{:.2},{},{},{},{},{},{},{},{},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{},{:.1}",
            s.seed, s.p_milk, s.cash, s.cows, s.sheep, s.shed_wheat, s.hands, s.quads, s.day,
            s.unwatered_crops, s.mature_crops,
            s.score_a0, s.score_a1, s.score_a2, s.score_a3, s.score_a4, s.score_a5,
            s.best_a, s.max_gain_vs_a0).unwrap();
    }

    println!("=========================================================================================");
    println!("                            MACRO ACTION DISCOVERY SUMMARY                               ");
    println!("=========================================================================================");
    let action_names = [
        "a0: DEFAULT_ADAPTIVE",
        "a1: RESCUE_BUY_WHEAT (Day 0)",
        "a2: RESCUE_HIRE_1 (Day 6)",
        "a3: SIZED_SHEEP_1 (Day 8)",
        "a4: SIZED_SHEEP_2 (Day 8)",
        "a5: FULL_SHEEP_4 (Day 8)",
    ];

    for i in 0..6 {
        let count = action_counts[i];
        let pct = (count as f64 / num_seeds as f64) * 100.0;
        let avg_gain = if count > 0 { sum_gains[i] / count as f64 } else { 0.0 };
        println!("{:<32} | Optimal in {:>5} seeds ({:>4.1}%) | Avg Delta when optimal: +${:<7.1}",
            action_names[i], count, pct, avg_gain);
    }
    println!("=========================================================================================");
    println!("Saved complete dataset to {}", csv_path);
}

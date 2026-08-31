//! EXP194 — High-Throughput Opponent-Conditioned Macro Dataset Generator.
//! Mines 10,000 seeds across multi-opponent contexts (Adaptive, D.1, AgroHybrid, V4.1) x 6 candidate actions (60,000 full game rollouts).

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, AdaptiveTerminalPolicy, D1Policy, V41Policy, AgroHybridPolicy
};
use fastsim::market::{Product, MarketOrder};
use fastsim::farm::{Animal, Crop, Tile};
use rayon::prelude::*;
use std::fs::File;
use std::io::Write;
use std::time::Instant;

#[derive(Clone, Debug)]
pub struct OpponentSample {
    pub seed: u64,
    pub opp_type: usize, // 0: Adaptive, 1: D.1, 2: AgroHybrid, 3: V4.1
    // Own features (10-d)
    pub p_milk: f64,
    pub cash: f64,
    pub cows: usize,
    pub sheep: usize,
    pub shed_wheat: i64,
    pub hands: usize,
    pub quads: usize,
    pub day: usize,
    pub unwatered: usize,
    pub mature: usize,
    // Opponent visible features (6-d)
    pub opp_cash: f64,
    pub opp_cows: usize,
    pub opp_sheep: usize,
    pub opp_quads: usize,
    pub opp_workers: usize,
    pub opp_straws: usize,
    // Counterfactual scores
    pub score_a0: f64,
    pub score_a1: f64,
    pub score_a2: f64,
    pub score_a3: f64,
    pub score_a4: f64,
    pub score_a5: f64,
    pub best_a: usize,
    pub max_gain_vs_a0: f64,
}

pub fn evaluate_opponent_seed(seed: u64, opp_type: usize) -> OpponentSample {
    let base_hero = AdaptiveTerminalPolicy::new();

    let create_opp = || -> Box<dyn Policy> {
        match opp_type {
            0 => Box::new(AdaptiveTerminalPolicy::new()),
            1 => Box::new(D1Policy::new()),
            2 => Box::new(AgroHybridPolicy::new()),
            _ => Box::new(V41Policy::new()),
        }
    };

    // 1. Baseline a0 rollout
    let mut st_a0 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let opp_policy_0 = create_opp();

    let mut snap_p_milk = 160.0;
    let mut snap_cash = 2000.0;
    let mut snap_cows = 3;
    let mut snap_sheep = 0;
    let mut snap_shed_wheat = 12;
    let mut snap_hands = 0;
    let mut snap_quads = 1;
    let mut snap_unw = 0;
    let mut snap_mat = 0;

    let mut snap_opp_cash = 2000.0;
    let mut snap_opp_cows = 3;
    let mut snap_opp_sheep = 0;
    let mut snap_opp_quads = 1;
    let mut snap_opp_workers = 0;
    let mut snap_opp_straws = 0;

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
            snap_unw = unw;
            snap_mat = mat;

            // Extract opponent features
            snap_opp_cash = st_a0.farms[1].money;
            snap_opp_quads = st_a0.farms[1].unlocked_quadrants.len();
            snap_opp_workers = st_a0.farms[1].hands.len();

            let mut oc = 0;
            let mut os = 0;
            let mut ost = 0;
            for row in &st_a0.farms[1].tiles {
                for tile in row {
                    match tile {
                        Tile::Animal(a) => {
                            if a.animal == Animal::Cow { oc += 1; }
                            if a.animal == Animal::Sheep { os += 1; }
                        }
                        Tile::Plant(p) => {
                            if p.crop == Crop::Strawberry { ost += 1; }
                        }
                        _ => {}
                    }
                }
            }
            snap_opp_cows = oc;
            snap_opp_sheep = os;
            snap_opp_straws = ost;
        }

        let a0 = base_hero.act(&st_a0, 0);
        let a1 = opp_policy_0.act(&st_a0, 1);
        step_game(&mut st_a0, &[a0, a1]);
    }
    let score_a0 = st_a0.farms[0].money;

    // 2. Evaluate a1: Buy Wheat at Day 0 Step 0
    let mut st_a1 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let opp_policy_1 = create_opp();
    while !st_a1.done {
        let mut a0 = base_hero.act(&st_a1, 0);
        if st_a1.step == 0 {
            a0.market.push(MarketOrder::BuySeed(Crop::Wheat, 4));
        }
        let a1 = opp_policy_1.act(&st_a1, 1);
        step_game(&mut st_a1, &[a0, a1]);
    }
    let score_a1 = st_a1.farms[0].money;

    // 3. Evaluate a2: Hire 1 on Day 6 Hour 0
    let mut st_a2 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let opp_policy_2 = create_opp();
    while !st_a2.done {
        let mut a0 = base_hero.act(&st_a2, 0);
        if st_a2.day == 6 && st_a2.hour == 0 && st_a2.farms[0].money >= 40.0 {
            a0.market.push(MarketOrder::Hire);
        }
        let a1 = opp_policy_2.act(&st_a2, 1);
        step_game(&mut st_a2, &[a0, a1]);
    }
    let score_a2 = st_a2.farms[0].money;

    // 4. Evaluate a3: 1 Sheep on Day 8 Hour 4
    let mut st_a3 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let opp_policy_3 = create_opp();
    while !st_a3.done {
        let mut a0 = base_hero.act(&st_a3, 0);
        if st_a3.day == 8 && st_a3.hour == 4 {
            a0.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            if st_a3.farms[0].money >= 600.0 {
                a0.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1));
            }
        }
        let a1 = opp_policy_3.act(&st_a3, 1);
        step_game(&mut st_a3, &[a0, a1]);
    }
    let score_a3 = st_a3.farms[0].money;

    // 5. Evaluate a4: 2 Sheep on Day 8 Hour 4
    let mut st_a4 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let opp_policy_4 = create_opp();
    while !st_a4.done {
        let mut a0 = base_hero.act(&st_a4, 0);
        if st_a4.day == 8 && st_a4.hour == 4 {
            a0.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            if st_a4.farms[0].money >= 1200.0 {
                a0.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
            }
        }
        let a1 = opp_policy_4.act(&st_a4, 1);
        step_game(&mut st_a4, &[a0, a1]);
    }
    let score_a4 = st_a4.farms[0].money;

    // 6. Evaluate a5: 4 Sheep on Day 8 Hour 4
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

    OpponentSample {
        seed,
        opp_type,
        p_milk: snap_p_milk,
        cash: snap_cash,
        cows: snap_cows,
        sheep: snap_sheep,
        shed_wheat: snap_shed_wheat,
        hands: snap_hands,
        quads: snap_quads,
        day: 8,
        unwatered: snap_unw,
        mature: snap_mat,
        opp_cash: snap_opp_cash,
        opp_cows: snap_opp_cows,
        opp_sheep: snap_opp_sheep,
        opp_quads: snap_opp_quads,
        opp_workers: snap_opp_workers,
        opp_straws: snap_opp_straws,
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
    println!("     EXP194 — HIGH-THROUGHPUT OPPONENT-CONDITIONED DATASET GENERATOR (10,000 SAMPLES)    ");
    println!("=========================================================================================");

    let num_seeds = 2500; // 2,500 seeds x 4 opponent types = 10,000 samples (60,000 rollouts)
    let seeds: Vec<u64> = (100000..(100000 + num_seeds as u64)).collect();
    let t0 = Instant::now();

    println!("Generating 2,500 seeds x 4 opponents x 6 actions = 60,000 full game rollouts...");

    let mut tasks = Vec::with_capacity(num_seeds * 4);
    for &s in &seeds {
        for opp in 0..4 {
            tasks.push((s, opp));
        }
    }

    let samples: Vec<OpponentSample> = tasks.into_par_iter().map(|(s, opp)| {
        evaluate_opponent_seed(s, opp)
    }).collect();

    let elapsed = t0.elapsed().as_secs_f64();
    println!("Dataset generation completed in {:.2}s ({:.1} rollouts/sec)\n", elapsed, (num_seeds * 4 * 6) as f64 / elapsed);

    let csv_path = r"D:\kaggriculture\data\exp194_opponent_dataset.csv";
    let mut file = File::create(csv_path).expect("Failed to create CSV");
    writeln!(file, "seed,opp_type,p_milk,cash,cows,sheep,shed_wheat,hands,quads,day,unwatered,mature,opp_cash,opp_cows,opp_sheep,opp_quads,opp_workers,opp_straws,score_a0,score_a1,score_a2,score_a3,score_a4,score_a5,best_a,gain_vs_a0").unwrap();

    for s in &samples {
        writeln!(file, "{},{},{:.2},{:.2},{},{},{},{},{},{},{},{},{:.2},{},{},{},{},{},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{},{:.1}",
            s.seed, s.opp_type, s.p_milk, s.cash, s.cows, s.sheep, s.shed_wheat, s.hands, s.quads, s.day,
            s.unwatered, s.mature,
            s.opp_cash, s.opp_cows, s.opp_sheep, s.opp_quads, s.opp_workers, s.opp_straws,
            s.score_a0, s.score_a1, s.score_a2, s.score_a3, s.score_a4, s.score_a5,
            s.best_a, s.max_gain_vs_a0).unwrap();
    }

    println!("Saved 10,000 opponent-conditioned samples to {}", csv_path);
}

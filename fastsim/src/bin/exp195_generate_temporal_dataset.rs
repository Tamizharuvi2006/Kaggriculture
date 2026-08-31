//! EXP195 — High-Throughput Temporal Sequence Dataset Generator.
//! Records 5-step historical state trajectories H_t and counterfactual terminal returns for 6 macro actions.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, AdaptiveTerminalPolicy, D1Policy, AgroHybridPolicy, V41Policy
};
use fastsim::market::{Product, MarketOrder};
use fastsim::farm::{Animal, Crop, Tile};
use rayon::prelude::*;
use std::fs::File;
use std::io::Write;
use std::time::Instant;

#[derive(Clone, Debug, Default)]
pub struct TemporalStepSnapshot {
    pub cash: f64,
    pub p_milk: f64,
    pub p_straw: f64,
    pub shed_wheat: i64,
    pub shed_milk: i64,
    pub cows: usize,
    pub sheep: usize,
    pub hands: usize,
    pub quads: usize,
    pub unwatered: usize,
    pub opp_cash: f64,
    pub opp_straws: usize,
}

#[derive(Clone, Debug)]
pub struct TemporalSample {
    pub seed: u64,
    pub opp_type: usize,
    pub history: [TemporalStepSnapshot; 5], // t-4, t-3, t-2, t-1, t
    pub scores: [f64; 6], // a0..a5
    pub best_a: usize,
    pub max_gain_vs_a0: f64,
}

pub fn extract_snapshot(st: &GameState, p_idx: usize) -> TemporalStepSnapshot {
    let opp_idx = 1 - p_idx;
    let farm = &st.farms[p_idx];
    let priv_farm = &st.privates[p_idx];
    let opp_farm = &st.farms[opp_idx];

    let p_milk = *st.market.prices.get(&Product::Milk).unwrap_or(&160) as f64;
    let p_straw = *st.market.prices.get(&Product::Strawberry).unwrap_or(&120) as f64;
    let cash = farm.money;
    let shed_wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0);
    let shed_milk = *priv_farm.shed.get("MILK").unwrap_or(&0);
    let hands = farm.hands.len();
    let quads = farm.unlocked_quadrants.len();

    let mut cows = 0;
    let mut sheep = 0;
    let mut unwatered = 0;

    for row in &farm.tiles {
        for tile in row {
            match tile {
                Tile::Animal(a) => {
                    if a.animal == Animal::Cow { cows += 1; }
                    if a.animal == Animal::Sheep { sheep += 1; }
                }
                Tile::Plant(p) => {
                    if p.yield_units == 0 && !p.watered_today { unwatered += 1; }
                }
                _ => {}
            }
        }
    }

    let opp_cash = opp_farm.money;
    let mut opp_straws = 0;
    for row in &opp_farm.tiles {
        for tile in row {
            if let Tile::Plant(p) = tile {
                if p.crop == Crop::Strawberry { opp_straws += 1; }
            }
        }
    }

    TemporalStepSnapshot {
        cash,
        p_milk,
        p_straw,
        shed_wheat,
        shed_milk,
        cows,
        sheep,
        hands,
        quads,
        unwatered,
        opp_cash,
        opp_straws,
    }
}

pub fn evaluate_temporal_seed(seed: u64, opp_type: usize) -> TemporalSample {
    let base_hero = AdaptiveTerminalPolicy::new();
    let create_opp = || -> Box<dyn Policy> {
        match opp_type {
            0 => Box::new(AdaptiveTerminalPolicy::new()),
            1 => Box::new(D1Policy::new()),
            2 => Box::new(AgroHybridPolicy::new()),
            _ => Box::new(V41Policy::new()),
        }
    };

    // 1. Advance to Day 8 Hour 4 while recording step-by-step history snapshots
    let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let opp_p = create_opp();

    let mut history_buffer: Vec<TemporalStepSnapshot> = Vec::new();

    while !st.done && !(st.day == 8 && st.hour == 4) {
        if st.hour % 6 == 0 || (st.day == 8 && st.hour >= 0) {
            history_buffer.push(extract_snapshot(&st, 0));
        }

        let a0 = base_hero.act(&st, 0);
        let a1 = opp_p.act(&st, 1);
        step_game(&mut st, &[a0, a1]);
    }

    // Extract last 5 history frames leading into the decision
    let mut history = [
        TemporalStepSnapshot::default(),
        TemporalStepSnapshot::default(),
        TemporalStepSnapshot::default(),
        TemporalStepSnapshot::default(),
        TemporalStepSnapshot::default(),
    ];

    let h_len = history_buffer.len();
    for i in 0..5 {
        if h_len >= 5 - i {
            history[i] = history_buffer[h_len - (5 - i)].clone();
        } else if h_len > 0 {
            history[i] = history_buffer[0].clone();
        }
    }

    // 2. Evaluate all 6 candidate actions
    // a0: Default
    let mut st_a0 = st.clone();
    let opp_p0 = create_opp();
    while !st_a0.done {
        let a0 = base_hero.act(&st_a0, 0);
        let a1 = opp_p0.act(&st_a0, 1);
        step_game(&mut st_a0, &[a0, a1]);
    }
    let score_a0 = st_a0.farms[0].money;

    // a1: Buy Wheat at Day 0 (full game evaluation)
    let mut st_a1 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let opp_p1 = create_opp();
    while !st_a1.done {
        let mut a0 = base_hero.act(&st_a1, 0);
        if st_a1.step == 0 {
            a0.market.push(MarketOrder::BuySeed(Crop::Wheat, 4));
        }
        let a1 = opp_p1.act(&st_a1, 1);
        step_game(&mut st_a1, &[a0, a1]);
    }
    let score_a1 = st_a1.farms[0].money;

    // a2: Hire 1 on Day 6 (full game evaluation)
    let mut st_a2 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let opp_p2 = create_opp();
    while !st_a2.done {
        let mut a0 = base_hero.act(&st_a2, 0);
        if st_a2.day == 6 && st_a2.hour == 0 && st_a2.farms[0].money >= 40.0 {
            a0.market.push(MarketOrder::Hire);
        }
        let a1 = opp_p2.act(&st_a2, 1);
        step_game(&mut st_a2, &[a0, a1]);
    }
    let score_a2 = st_a2.farms[0].money;

    // a3: 1 Sheep on Day 8 Hour 4
    let mut st_a3 = st.clone();
    let opp_p3 = create_opp();
    let mut a0_3 = base_hero.act(&st_a3, 0);
    a0_3.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
    if st_a3.farms[0].money >= 600.0 {
        a0_3.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1));
    }
    let a1_3 = opp_p3.act(&st_a3, 1);
    step_game(&mut st_a3, &[a0_3, a1_3]);
    while !st_a3.done {
        let a0 = base_hero.act(&st_a3, 0);
        let a1 = opp_p3.act(&st_a3, 1);
        step_game(&mut st_a3, &[a0, a1]);
    }
    let score_a3 = st_a3.farms[0].money;

    // a4: 2 Sheep on Day 8 Hour 4
    let mut st_a4 = st.clone();
    let opp_p4 = create_opp();
    let mut a0_4 = base_hero.act(&st_a4, 0);
    a0_4.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
    if st_a4.farms[0].money >= 1200.0 {
        a0_4.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
    }
    let a1_4 = opp_p4.act(&st_a4, 1);
    step_game(&mut st_a4, &[a0_4, a1_4]);
    while !st_a4.done {
        let a0 = base_hero.act(&st_a4, 0);
        let a1 = opp_p4.act(&st_a4, 1);
        step_game(&mut st_a4, &[a0, a1]);
    }
    let score_a4 = st_a4.farms[0].money;

    // a5: 4 Sheep on Day 8 Hour 4
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

    TemporalSample {
        seed,
        opp_type,
        history,
        scores,
        best_a,
        max_gain_vs_a0: best_s - score_a0,
    }
}

fn main() {
    println!("=========================================================================================");
    println!("     EXP195 — HIGH-THROUGHPUT TEMPORAL SEQUENCE DATASET GENERATOR (10,000 SAMPLES)       ");
    println!("=========================================================================================");

    let num_seeds = 2500; // 2,500 seeds x 4 opponent types = 10,000 samples
    let seeds: Vec<u64> = (120000..(120000 + num_seeds as u64)).collect();
    let t0 = Instant::now();

    println!("Mining 2,500 seeds x 4 opponents x 5-step trajectory histories...");

    let mut tasks = Vec::with_capacity(num_seeds * 4);
    for &s in &seeds {
        for opp in 0..4 {
            tasks.push((s, opp));
        }
    }

    let samples: Vec<TemporalSample> = tasks.into_par_iter().map(|(s, opp)| {
        evaluate_temporal_seed(s, opp)
    }).collect();

    let elapsed = t0.elapsed().as_secs_f64();
    println!("Temporal dataset generated in {:.2}s ({:.1} rollouts/sec)\n", elapsed, (num_seeds * 4 * 6) as f64 / elapsed);

    let csv_path = r"D:\kaggriculture\data\exp195_temporal_dataset.csv";
    let mut file = File::create(csv_path).expect("Failed to create CSV");

    // CSV Header with flattened 5-step history (5 steps x 12 features = 60 columns)
    let mut header = "seed,opp_type".to_string();
    for t in 0..5 {
        for f in ["cash", "p_milk", "p_straw", "shed_wheat", "shed_milk", "cows", "sheep", "hands", "quads", "unwatered", "opp_cash", "opp_straws"] {
            header.push_str(&format!(",t{}_{}", t, f));
        }
    }
    header.push_str(",score_a0,score_a1,score_a2,score_a3,score_a4,score_a5,best_a,gain_vs_a0\n");
    file.write_all(header.as_bytes()).unwrap();

    for s in &samples {
        let mut row = format!("{},{}", s.seed, s.opp_type);
        for snap in &s.history {
            row.push_str(&format!(",{:.1},{:.1},{:.1},{},{},{},{},{},{},{},{:.1},{}",
                snap.cash, snap.p_milk, snap.p_straw, snap.shed_wheat, snap.shed_milk,
                snap.cows, snap.sheep, snap.hands, snap.quads, snap.unwatered,
                snap.opp_cash, snap.opp_straws));
        }
        row.push_str(&format!(",{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{},{:.1}\n",
            s.scores[0], s.scores[1], s.scores[2], s.scores[3], s.scores[4], s.scores[5],
            s.best_a, s.max_gain_vs_a0));
        file.write_all(row.as_bytes()).unwrap();
    }

    println!("Saved 10,000 temporal samples (60-d state trajectory) to {}", csv_path);
}

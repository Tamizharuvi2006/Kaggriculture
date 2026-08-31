//! EXP191 — High-Throughput State-Conditioned Sheep Q Search & Decision Surface Mapper.
//! Evaluates 5,000 seeds x 5 sheep sizing decisions (0, 1, 2, 3, 4 Sheep) across multi-dimensional states.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};
use fastsim::market::{Product, MarketOrder};
use fastsim::farm::Animal;
use rayon::prelude::*;
use std::fs::File;
use std::io::Write;
use std::time::Instant;

#[derive(Clone, Debug)]
pub struct SheepQSample {
    pub seed: u64,
    pub p_milk: f64,
    pub cash: f64,
    pub cow_count: usize,
    pub shed_wheat: i64,
    pub hands: usize,
    pub quads: usize,
    pub score_0: f64,
    pub score_1: f64,
    pub score_2: f64,
    pub score_3: f64,
    pub score_4: f64,
    pub best_n: usize,
    pub max_gain_vs_base4: f64,
}

pub fn evaluate_seed_sheep_sweep(seed: u64) -> SheepQSample {
    let base_policy = AdaptiveTerminalPolicy::new();
    let opp_policy = AdaptiveTerminalPolicy::new();

    // 1. Advance baseline up to Day 8 Hour 4
    let mut checkpoint_state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    while !checkpoint_state.done && !(checkpoint_state.day == 8 && checkpoint_state.hour == 4) {
        let a0 = base_policy.act(&checkpoint_state, 0);
        let a1 = opp_policy.act(&checkpoint_state, 1);
        step_game(&mut checkpoint_state, &[a0, a1]);
    }

    let p_milk = *checkpoint_state.market.prices.get(&Product::Milk).unwrap_or(&160) as f64;
    let cash = checkpoint_state.farms[0].money;
    let shed_wheat = *checkpoint_state.privates[0].shed.get("WHEAT").unwrap_or(&0);
    let hands = checkpoint_state.farms[0].hands.len();
    let quads = checkpoint_state.farms[0].unlocked_quadrants.len();

    let mut cow_count = 0;
    for row in &checkpoint_state.farms[0].tiles {
        for tile in row {
            if let fastsim::farm::Tile::Animal(a) = tile {
                if a.animal == Animal::Cow { cow_count += 1; }
            }
        }
    }

    let mut scores = [0.0; 5];

    // 2. Evaluate 5 sheep sizing decisions (0, 1, 2, 3, 4) from this exact checkpoint
    for n in 0..=4 {
        let mut sim_st = checkpoint_state.clone();
        let mut a0 = base_policy.act(&sim_st, 0);

        // Replace baseline sheep orders with N sheep
        a0.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
        if n > 0 {
            let cost = 600.0 * (n as f64);
            if sim_st.farms[0].money >= cost {
                a0.market.push(MarketOrder::BuyAnimal(Animal::Sheep, n as i64));
            }
        }

        let a1 = opp_policy.act(&sim_st, 1);
        step_game(&mut sim_st, &[a0, a1]);

        while !sim_st.done {
            let a0_step = base_policy.act(&sim_st, 0);
            let a1_step = opp_policy.act(&sim_st, 1);
            step_game(&mut sim_st, &[a0_step, a1_step]);
        }

        scores[n] = sim_st.farms[0].money;
    }

    let mut best_n = 4;
    let mut best_score = scores[4];
    for n in 0..=4 {
        if scores[n] > best_score + 1.0 {
            best_score = scores[n];
            best_n = n;
        }
    }

    SheepQSample {
        seed,
        p_milk,
        cash,
        cow_count,
        shed_wheat,
        hands,
        quads,
        score_0: scores[0],
        score_1: scores[1],
        score_2: scores[2],
        score_3: scores[3],
        score_4: scores[4],
        best_n,
        max_gain_vs_base4: best_score - scores[4],
    }
}

fn main() {
    println!("=========================================================================================");
    println!("       EXP191 — HIGH-THROUGHPUT STATE-CONDITIONED SHEEP Q SEARCH (5,000 SEEDS)           ");
    println!("=========================================================================================");

    let num_seeds = 5000;
    let seeds: Vec<u64> = (40000..(40000 + num_seeds as u64)).collect();
    let t0 = Instant::now();

    println!("Running 5,000 seeds x 5 counterfactual options = 25,000 full-game rollouts...");
    let samples: Vec<SheepQSample> = seeds.into_par_iter().map(evaluate_seed_sheep_sweep).collect();
    let elapsed = t0.elapsed().as_secs_f64();

    println!("Search Completed in {:.2}s ({:.1} rollouts/sec)\n", elapsed, (num_seeds * 5) as f64 / elapsed);

    // Bins for 2D Decision Surface
    let p_bins = [
        ("Milk < $140 (Crashed)", 0.0, 140.0),
        ("Milk $140–$175 (Low)", 140.0, 175.0),
        ("Milk $175–$210 (Normal)", 175.0, 210.0),
        ("Milk > $210 (High Demand)", 210.0, 9999.0),
    ];

    let cash_bins = [
        ("Cash < $1,400 (Insolvent Danger)", 0.0, 1400.0),
        ("Cash $1,400–$1,800 (Tight Buffer)", 1400.0, 1800.0),
        ("Cash $1,800–$2,400 (Moderate)", 1800.0, 2400.0),
        ("Cash > $2,400 (Flush Capital)", 2400.0, 99999.0),
    ];

    println!("=========================================================================================================================");
    println!("                  EXP191 EMPIRICAL 2D DECISION SURFACE: OPTIMAL SHEEP SIZING BY REGIME                                  ");
    println!("=========================================================================================================================");
    println!("{:<28} | {:<32} | {:<7} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {:<15}",
        "Milk Price Band", "Cash Regime", "Samples", "0 Sheep", "1 Sheep", "2 Sheep", "3 Sheep", "4 Sheep", "Optimal N* (Gain)");
    println!("-------------------------------------------------------------------------------------------------------------------------");

    let mut optimal_table: Vec<(usize, usize, usize)> = Vec::new();

    for (p_idx, &(p_name, p_min, p_max)) in p_bins.iter().enumerate() {
        for (c_idx, &(c_name, c_min, c_max)) in cash_bins.iter().enumerate() {
            let cell_samples: Vec<&SheepQSample> = samples.iter().filter(|s| {
                s.p_milk >= p_min && s.p_milk < p_max && s.cash >= c_min && s.cash < c_max
            }).collect();

            if !cell_samples.is_empty() {
                let n = cell_samples.len() as f64;
                let mean_0 = cell_samples.iter().map(|s| s.score_0).sum::<f64>() / n;
                let mean_1 = cell_samples.iter().map(|s| s.score_1).sum::<f64>() / n;
                let mean_2 = cell_samples.iter().map(|s| s.score_2).sum::<f64>() / n;
                let mean_3 = cell_samples.iter().map(|s| s.score_3).sum::<f64>() / n;
                let mean_4 = cell_samples.iter().map(|s| s.score_4).sum::<f64>() / n;

                let means = [mean_0, mean_1, mean_2, mean_3, mean_4];
                let mut best_n = 4;
                let mut best_m = mean_4;
                for (s_idx, &m) in means.iter().enumerate() {
                    if m > best_m + 50.0 { // Require statistically meaningful threshold
                        best_m = m;
                        best_n = s_idx;
                    }
                }

                optimal_table.push((p_idx, c_idx, best_n));

                println!("{:<28} | {:<32} | {:<7} | ${:<9.0} | ${:<9.0} | ${:<9.0} | ${:<9.0} | ${:<9.0} | ★ {} (+${:.0})",
                    p_name, c_name, cell_samples.len(),
                    mean_0, mean_1, mean_2, mean_3, mean_4,
                    best_n, best_m - mean_4);
            }
        }
    }

    println!("=========================================================================================================================");

    // Save dataset to CSV for forensic reference
    let csv_path = r"D:\kaggriculture\data\exp191_sheep_q_dataset.csv";
    let mut file = File::create(csv_path).expect("Failed to create CSV");
    writeln!(file, "seed,p_milk,cash,cow_count,shed_wheat,hands,quads,score_0,score_1,score_2,score_3,score_4,best_n,gain_vs_base4").unwrap();
    for s in &samples {
        writeln!(file, "{},{:.2},{:.2},{},{},{},{},{:.1},{:.1},{:.1},{:.1},{:.1},{},{:.1}",
            s.seed, s.p_milk, s.cash, s.cow_count, s.shed_wheat, s.hands, s.quads,
            s.score_0, s.score_1, s.score_2, s.score_3, s.score_4, s.best_n, s.max_gain_vs_base4).unwrap();
    }
    println!("Saved 5,000-seed dataset to {}", csv_path);
}

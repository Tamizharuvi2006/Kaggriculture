//! EXP189 — Day 8 Milk Price vs Cash vs Animal Purchase Decision Surface.
//! Evaluates the 2D grid (Milk Price x Available Cash x Sheep Purchase Count) across 2,000 seeds.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};
use fastsim::market::{Product, MarketOrder};
use fastsim::farm::Animal;
use rayon::prelude::*;
use std::time::Instant;

#[derive(Clone, Debug)]
pub struct SurfacePoint {
    pub p_milk_bin: usize, // 100-130, 130-160, 160-190, 190-220, 220+
    pub cash_bin: usize,   // <1500, 1500-2200, 2200-3000, 3000+
    pub sheep_count: usize,// 0, 1, 2, 3, 4
    pub seed: u64,
    pub terminal_score: f64,
    pub hit_zero_cash: bool,
}

pub fn evaluate_scenario(seed: u64, forced_sheep: usize) -> (f64, bool, f64, f64) {
    let base_policy = AdaptiveTerminalPolicy::new();
    let opp_policy = AdaptiveTerminalPolicy::new();
    let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);

    let mut recorded_p_milk = 160.0;
    let mut recorded_cash = 2000.0;
    let mut hit_zero_cash = false;

    while !st.done {
        let day = st.day;
        let hour = st.hour;
        let mut a0 = base_policy.act(&st, 0);

        if day == 8 && hour == 4 {
            recorded_p_milk = *st.market.prices.get(&Product::Milk).unwrap_or(&160) as f64;
            recorded_cash = st.farms[0].money;

            // Replace baseline sheep orders with forced_sheep count
            a0.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            if forced_sheep > 0 {
                let cost = 600.0 * (forced_sheep as f64);
                if st.farms[0].money >= cost {
                    a0.market.push(MarketOrder::BuyAnimal(Animal::Sheep, forced_sheep as i64));
                }
            }

        } else if day == 8 && hour > 4 && hour <= 10 {
            // Check if cash went to $0
            if st.farms[0].money <= 5.0 {
                hit_zero_cash = true;
            }
        }

        let a1 = opp_policy.act(&st, 1);
        step_game(&mut st, &[a0, a1]);
    }

    (st.farms[0].money, hit_zero_cash, recorded_p_milk, recorded_cash)
}

fn main() {
    println!("=========================================================================================");
    println!("       EXP189 — MAPPING DAY 8 MILK PRICE vs CASH vs ANIMAL PURCHASE DECISION SURFACE    ");
    println!("=========================================================================================");

    let num_seeds = 2000;
    let seeds: Vec<u64> = (30000..(30000 + num_seeds as u64)).collect();
    let t0 = Instant::now();

    println!("Running 2,000 seeds x 5 sheep arms (0, 1, 2, 3, 4 Sheep) = 10,000 full game rollouts...");

    let results: Vec<Vec<(usize, f64, bool, f64, f64)>> = seeds.into_par_iter().map(|seed| {
        let mut seed_res = Vec::new();
        for sheep in 0..=4 {
            let (score, zero_cash, p_milk, cash) = evaluate_scenario(seed, sheep);
            seed_res.push((sheep, score, zero_cash, p_milk, cash));
        }
        seed_res
    }).collect();

    let elapsed = t0.elapsed().as_secs_f64();
    println!("Simulations completed in {:.2}s ({:.1} rollouts/sec)\n", elapsed, (num_seeds * 5) as f64 / elapsed);

    // Bin definitions
    let p_bins = [
        ("P_milk < $140 (Crashed)", 0.0, 140.0),
        ("P_milk $140–$175 (Low)", 140.0, 175.0),
        ("P_milk $175–$210 (Normal)", 175.0, 210.0),
        ("P_milk > $210 (High Demand)", 210.0, 9999.0),
    ];

    let cash_bins = [
        ("Cash < $1,800 (Tight)", 0.0, 1800.0),
        ("Cash $1,800–$2,500 (Moderate)", 1800.0, 2500.0),
        ("Cash > $2,500 (Flush)", 2500.0, 99999.0),
    ];

    println!("=========================================================================================================================");
    println!("                       DECISION SURFACE MATRIX: MEAN REWARD ($) BY MILK PRICE & CASH REGIME                              ");
    println!("=========================================================================================================================");

    for &(p_name, p_min, p_max) in &p_bins {
        println!("\n>>> {} <<<", p_name);
        println!("{:<30} | {:<12} | {:<12} | {:<12} | {:<12} | {:<12} | {:<15}",
            "Cash Regime", "0 Sheep", "1 Sheep", "2 Sheep", "3 Sheep", "4 Sheep (Base)", "Optimal Policy");
        println!("-------------------------------------------------------------------------------------------------------------------------");

        for &(c_name, c_min, c_max) in &cash_bins {
            let mut sheep_scores = vec![Vec::new(); 5];
            let mut sheep_bankrupt_rates = vec![0.0; 5];
            let mut total_in_cell = 0;

            for r in &results {
                let p_milk = r[0].3;
                let cash = r[0].4;

                if p_milk >= p_min && p_milk < p_max && cash >= c_min && cash < c_max {
                    total_in_cell += 1;
                    for sheep in 0..=4 {
                        sheep_scores[sheep].push(r[sheep].1);
                        if r[sheep].2 {
                            sheep_bankrupt_rates[sheep] += 1.0;
                        }
                    }
                }
            }

            if total_in_cell > 0 {
                let means: Vec<f64> = sheep_scores.iter().map(|s| {
                    if !s.is_empty() { s.iter().sum::<f64>() / s.len() as f64 } else { 0.0 }
                }).collect();

                let mut best_sheep = 0;
                let mut best_mean = means[0];
                for (s, &m) in means.iter().enumerate() {
                    if m > best_mean {
                        best_mean = m;
                        best_sheep = s;
                    }
                }

                println!("{:<30} | ${:<11.0} | ${:<11.0} | ${:<11.0} | ${:<11.0} | ${:<11.0} | ★ {} Sheep (+${:.0})",
                    format!("{} (N={})", c_name, total_in_cell),
                    means[0], means[1], means[2], means[3], means[4],
                    best_sheep, best_mean - means[4]);
            }
        }
    }
    println!("=========================================================================================================================");
}

//! EXP201 — Elite Frontier Macro Action Space Miner (Full Game Horizons: Day 0 to Day 29).
//! Evaluates a comprehensive macro decision grid across 6 game phases against competitive 1v1 opponents.
//! Uses 2-player dynamic simulation to measure true Competitive Margin Delta across 12 candidate macro actions.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy, D1Policy};
use fastsim::market::{Product, MarketOrder};
use fastsim::farm::{Animal, Crop, Tile, Quadrant};
use rayon::prelude::*;
use std::fs::File;
use std::io::Write;
use std::time::Instant;

/// Macro actions covering all 6 game phases
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum MacroAction {
    DefaultAdaptive,            // a0: Pure Adaptive Chassis
    EarlyWheatInsuranceDay0,    // a1: Phase 1 (Day 0) - Buy 4 Wheat Seed
    EarlyHireDay1,              // a2: Phase 1 (Day 1) - Hire worker immediately
    LaborTransitionDay4,        // a3: Phase 2 (Day 4) - Hire worker 1 at Day 4
    LaborTransitionDay6,        // a4: Phase 2 (Day 6) - Hire worker 1 at Day 6
    SheepSized1Day8,            // a5: Phase 3 (Day 8) - Buy 1 Sheep
    SheepSized2Day8,            // a6: Phase 3 (Day 8) - Buy 2 Sheep
    SheepStandard4Day8,         // a7: Phase 3 (Day 8) - Buy 4 Sheep
    FourthLandExpansionDay12,   // a8: Phase 4 (Day 12) - Unlock Quadrant 4 (Land #4)
    LateStrawberryRotationDay16,// a9: Phase 5 (Day 16) - Plant all available tiles with Strawberry
    LateMelonTransitionDay18,   // a10: Phase 5 (Day 18) - High-value Melon pivot
    EndGameSellAnimalsDay26,    // a11: Phase 6 (Day 26) - Sell all livestock for cash liquidation
}

pub const NUM_MACRO_ACTIONS: usize = 12;

pub fn execute_macro_simulation(seed: u64, opp_type: usize, cand_act: MacroAction) -> (f64, f64) {
    let hero_policy = AdaptiveTerminalPolicy::new();
    let opp_policy: Box<dyn Policy> = if opp_type == 0 {
        Box::new(AdaptiveTerminalPolicy::new())
    } else {
        Box::new(D1Policy::new())
    };

    let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);

    while !st.done {
        let step = st.step;
        let day = st.day;
        let hour = st.hour;

        let mut a0 = hero_policy.act(&st, 0);

        match cand_act {
            MacroAction::EarlyWheatInsuranceDay0 => {
                if step == 0 {
                    a0.market.push(MarketOrder::BuySeed(Crop::Wheat, 4));
                }
            }
            MacroAction::EarlyHireDay1 => {
                if day == 1 && hour == 0 && st.farms[0].money >= 40.0 {
                    a0.market.push(MarketOrder::Hire);
                }
            }
            MacroAction::LaborTransitionDay4 => {
                if day == 4 && hour == 0 && st.farms[0].money >= 40.0 {
                    a0.market.push(MarketOrder::Hire);
                }
            }
            MacroAction::LaborTransitionDay6 => {
                if day == 6 && hour == 0 && st.farms[0].money >= 40.0 {
                    a0.market.push(MarketOrder::Hire);
                }
            }
            MacroAction::SheepSized1Day8 => {
                if day == 8 && hour == 4 {
                    a0.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                    if st.farms[0].money >= 600.0 {
                        a0.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1));
                    }
                }
            }
            MacroAction::SheepSized2Day8 => {
                if day == 8 && hour == 4 {
                    a0.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                    if st.farms[0].money >= 1200.0 {
                        a0.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
                    }
                }
            }
            MacroAction::SheepStandard4Day8 => {
                if day == 8 && hour == 4 {
                    a0.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                    if st.farms[0].money >= 2400.0 {
                        a0.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4));
                    }
                }
            }
            MacroAction::FourthLandExpansionDay12 => {
                if day == 12 && hour == 0 && st.farms[0].money >= 2000.0 && st.farms[0].unlocked_quadrants.len() < 4 {
                    a0.market.push(MarketOrder::BuyLand);
                }
            }
            MacroAction::LateStrawberryRotationDay16 => {
                if day == 16 && hour == 0 && st.farms[0].money >= 150.0 {
                    a0.market.push(MarketOrder::BuySeed(Crop::Strawberry, 10));
                }
            }
            MacroAction::LateMelonTransitionDay18 => {
                if day == 18 && hour == 0 && st.farms[0].money >= 200.0 {
                    a0.market.push(MarketOrder::BuySeed(Crop::Melon, 8));
                }
            }
            MacroAction::EndGameSellAnimalsDay26 => {
                // At Day 26 liquidation: sell all accumulated warehouse items immediately
                if day >= 26 && hour == 0 {
                    let milk = *st.privates[0].shed.get("MILK").unwrap_or(&0);
                    let wool = *st.privates[0].shed.get("WOOL").unwrap_or(&0);
                    let straw = *st.privates[0].shed.get("STRAWBERRY").unwrap_or(&0);
                    let melon = *st.privates[0].shed.get("MELON").unwrap_or(&0);
                    if milk > 0 { a0.market.push(MarketOrder::Sell(Product::Milk, milk)); }
                    if wool > 0 { a0.market.push(MarketOrder::Sell(Product::Wool, wool)); }
                    if straw > 0 { a0.market.push(MarketOrder::Sell(Product::Strawberry, straw)); }
                    if melon > 0 { a0.market.push(MarketOrder::Sell(Product::Melon, melon)); }
                }
            }
            MacroAction::DefaultAdaptive => {}
        }


        let a1 = opp_policy.act(&st, 1);
        step_game(&mut st, &[a0, a1]);
    }

    (st.farms[0].money, st.farms[1].money)
}

pub struct EliteHorizonSample {
    pub seed: u64,
    pub opp_type: usize,
    pub base_hero: f64,
    pub base_opp: f64,
    pub base_margin: f64,
    pub hero_scores: [f64; NUM_MACRO_ACTIONS],
    pub opp_scores: [f64; NUM_MACRO_ACTIONS],
    pub margin_deltas: [f64; NUM_MACRO_ACTIONS],
    pub solo_deltas: [f64; NUM_MACRO_ACTIONS],
    pub best_action_idx: usize,
    pub max_margin_delta: f64,
}

pub fn evaluate_elite_seed(seed: u64, opp_type: usize) -> EliteHorizonSample {
    let actions = [
        MacroAction::DefaultAdaptive,
        MacroAction::EarlyWheatInsuranceDay0,
        MacroAction::EarlyHireDay1,
        MacroAction::LaborTransitionDay4,
        MacroAction::LaborTransitionDay6,
        MacroAction::SheepSized1Day8,
        MacroAction::SheepSized2Day8,
        MacroAction::SheepStandard4Day8,
        MacroAction::FourthLandExpansionDay12,
        MacroAction::LateStrawberryRotationDay16,
        MacroAction::LateMelonTransitionDay18,
        MacroAction::EndGameSellAnimalsDay26,
    ];

    let mut hero_scores = [0.0; NUM_MACRO_ACTIONS];
    let mut opp_scores = [0.0; NUM_MACRO_ACTIONS];
    let mut margin_deltas = [0.0; NUM_MACRO_ACTIONS];
    let mut solo_deltas = [0.0; NUM_MACRO_ACTIONS];

    // 1. Run baseline a0
    let (base_hero, base_opp) = execute_macro_simulation(seed, opp_type, MacroAction::DefaultAdaptive);
    let base_margin = base_hero - base_opp;
    hero_scores[0] = base_hero;
    opp_scores[0] = base_opp;

    let mut best_act = 0;
    let mut max_margin = 0.0;

    for i in 1..NUM_MACRO_ACTIONS {
        let (h, o) = execute_macro_simulation(seed, opp_type, actions[i]);
        hero_scores[i] = h;
        opp_scores[i] = o;
        let cand_margin = h - o;
        let d_margin = cand_margin - base_margin;
        let d_solo = h - base_hero;

        margin_deltas[i] = d_margin;
        solo_deltas[i] = d_solo;

        if d_margin > max_margin + 50.0 {
            max_margin = d_margin;
            best_act = i;
        }
    }

    EliteHorizonSample {
        seed,
        opp_type,
        base_hero,
        base_opp,
        base_margin,
        hero_scores,
        opp_scores,
        margin_deltas,
        solo_deltas,
        best_action_idx: best_act,
        max_margin_delta: max_margin,
    }
}

fn main() {
    println!("=========================================================================================");
    println!("     EXP201 — ELITE FRONTIER MACRO HORIZON MINER (12 CANDIDATE ACTIONS, DAY 0–29)        ");
    println!("=========================================================================================");

    let n_matches = 2500; // 2,500 seeds x 2 opponents (Adaptive & D.1) = 5,000 matches (60,000 rollouts)
    let base_seed = 400000;

    let mut tasks = Vec::with_capacity(n_matches * 2);
    for s in 0..n_matches {
        tasks.push((base_seed + s as u64, 0)); // vs Adaptive Peak
        tasks.push((base_seed + 10000 + s as u64, 1)); // vs D.1 GM
    }

    let t0 = Instant::now();
    println!("Evaluating {} matches across 12 full-game macro actions (60,000 full rollouts)...", tasks.len());

    let samples: Vec<EliteHorizonSample> = tasks.into_par_iter().map(|(s, opp)| {
        evaluate_elite_seed(s, opp)
    }).collect();

    let elapsed = t0.elapsed().as_secs_f64();
    println!("Mining completed in {:.2}s ({:.1} rollouts/sec)\n", elapsed, (samples.len() * 12) as f64 / elapsed);

    let csv_path = r"D:\kaggriculture\data\exp201_elite_horizon_dataset.csv";
    let mut file = File::create(csv_path).expect("Failed to create CSV");
    writeln!(file, "seed,opp_type,base_hero,base_opp,base_margin,best_action,max_margin_delta").unwrap();

    let action_names = [
        "a0: Default Adaptive Chassis",
        "a1: Early Wheat Insurance (Day 0)",
        "a2: Early Hire Worker (Day 1)",
        "a3: Labor Transition 1 (Day 4)",
        "a4: Labor Transition 2 (Day 6)",
        "a5: Sized 1 Sheep (Day 8)",
        "a6: Sized 2 Sheep (Day 8)",
        "a7: Standard 4 Sheep (Day 8)",
        "a8: 4th Land Expansion (Day 12)",
        "a9: Late Strawberry Rotation (Day 16)",
        "a10: Late Melon Transition (Day 18)",
        "a11: End-Game Livestock Sale (Day 26)",
    ];

    let mut optimal_counts = [0; NUM_MACRO_ACTIONS];
    let mut optimal_margin_gains = [0.0; NUM_MACRO_ACTIONS];

    let mut q1_counts = [0; NUM_MACRO_ACTIONS]; // Solo > 0 & Margin > 0
    let mut q2_counts = [0; NUM_MACRO_ACTIONS]; // Solo > 0 & Margin <= 0 (Competitive Trap)

    for s in &samples {
        optimal_counts[s.best_action_idx] += 1;
        optimal_margin_gains[s.best_action_idx] += s.max_margin_delta;

        for i in 1..NUM_MACRO_ACTIONS {
            if s.solo_deltas[i] > 100.0 && s.margin_deltas[i] > 100.0 {
                q1_counts[i] += 1;
            } else if s.solo_deltas[i] > 100.0 && s.margin_deltas[i] <= 100.0 {
                q2_counts[i] += 1;
            }
        }

        writeln!(file, "{},{},{:.1},{:.1},{:.1},{},{:.1}",
            s.seed, s.opp_type, s.base_hero, s.base_opp, s.base_margin, s.best_action_idx, s.max_margin_delta).unwrap();
    }

    println!("=========================================================================================================================");
    println!("                                   EXP201 ELITE MACRO ACTION SCORECARD                                                   ");
    println!("=========================================================================================================================");
    println!("{:<36} | {:<12} | {:<18} | {:<14} | {:<14}",
        "Macro Action & Phase", "Optimal In", "Avg Margin Alpha", "True Alpha (Q1)", "Trap Rate (Q2)");
    println!("-------------------------------------------------------------------------------------------------------------------------");

    for i in 0..NUM_MACRO_ACTIONS {
        let cnt = optimal_counts[i];
        let pct = (cnt as f64 / samples.len() as f64) * 100.0;
        let avg_g = if cnt > 0 { optimal_margin_gains[i] / cnt as f64 } else { 0.0 };

        let q1 = q1_counts[i];
        let q2 = q2_counts[i];
        let total_pos = q1 + q2;
        let trap_pct = if total_pos > 0 { (q2 as f64 / total_pos as f64) * 100.0 } else { 0.0 };

        println!("{:<36} | {:>5} ({:>4.1}%) | {:>+15.1} | {:>6} matches  | {:>5.1}% trap",
            action_names[i], cnt, pct, avg_g, q1, trap_pct);
    }
    println!("=========================================================================================================================");
    println!("Saved complete EXP201 elite horizon dataset to {}", csv_path);
}

//! EXP200 — Competitive Margin Counterfactual Dataset Generator & Quadrant Analyzer.
//! Evaluates 10,000 matches (5,000 vs Adaptive, 5,000 vs D.1) across all candidate actions.
//! Computes exact 2-player dynamic rollouts, measures Solo Delta vs Competitive Margin Delta, and maps the 4 quadrants.

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

#[derive(Clone, Debug)]
pub struct CompetitiveSample {
    pub seed: u64,
    pub opp_type: usize, // 0: Adaptive (50%), 1: D.1 (50%)
    // 16-d State features
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
    pub opp_cash: f64,
    pub opp_cows: usize,
    pub opp_sheep: usize,
    pub opp_quads: usize,
    pub opp_workers: usize,
    pub opp_straws: usize,
    // Baseline returns
    pub base_hero: f64,
    pub base_opp: f64,
    pub base_margin: f64, // base_hero - base_opp
    // Candidate returns: [hero_score, opp_score, margin, solo_delta, margin_delta] for a0..a5
    pub scores_hero: [f64; 6],
    pub scores_opp: [f64; 6],
    pub margin_deltas: [f64; 6],
    pub best_competitive_a: usize,
    pub max_margin_gain: f64,
}

pub fn evaluate_competitive_seed(seed: u64, opp_type: usize) -> CompetitiveSample {
    let base_hero = AdaptiveTerminalPolicy::new();
    let create_opp = || -> Box<dyn Policy> {
        match opp_type {
            0 => Box::new(AdaptiveTerminalPolicy::new()),
            _ => Box::new(D1Policy::new()),
        }
    };

    // 1. Rollout Baseline (a0) vs live responsive opponent
    let mut st_a0 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let opp_p0 = create_opp();

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
        let a1 = opp_p0.act(&st_a0, 1);
        step_game(&mut st_a0, &[a0, a1]);
    }
    let base_hero_score = st_a0.farms[0].money;
    let base_opp_score = st_a0.farms[1].money;
    let base_margin = base_hero_score - base_opp_score;

    // 2. Evaluate a1: Buy Wheat at Day 0 (2-player responsive simulation)
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
    let a1_hero = st_a1.farms[0].money;
    let a1_opp = st_a1.farms[1].money;

    // 3. Evaluate a2: Hire 1 on Day 6 Hour 0
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
    let a2_hero = st_a2.farms[0].money;
    let a2_opp = st_a2.farms[1].money;

    // 4. Evaluate a3: 1 Sheep on Day 8 Hour 4
    let mut st_a3 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let opp_p3 = create_opp();
    while !st_a3.done {
        let mut a0 = base_hero.act(&st_a3, 0);
        if st_a3.day == 8 && st_a3.hour == 4 {
            a0.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            if st_a3.farms[0].money >= 600.0 {
                a0.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1));
            }
        }
        let a1 = opp_p3.act(&st_a3, 1);
        step_game(&mut st_a3, &[a0, a1]);
    }
    let a3_hero = st_a3.farms[0].money;
    let a3_opp = st_a3.farms[1].money;

    // 5. Evaluate a4: 2 Sheep on Day 8 Hour 4
    let mut st_a4 = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let opp_p4 = create_opp();
    while !st_a4.done {
        let mut a0 = base_hero.act(&st_a4, 0);
        if st_a4.day == 8 && st_a4.hour == 4 {
            a0.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            if st_a4.farms[0].money >= 1200.0 {
                a0.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
            }
        }
        let a1 = opp_p4.act(&st_a4, 1);
        step_game(&mut st_a4, &[a0, a1]);
    }
    let a4_hero = st_a4.farms[0].money;
    let a4_opp = st_a4.farms[1].money;

    // 6. Evaluate a5: 4 Sheep on Day 8 Hour 4 (same as a0)
    let a5_hero = base_hero_score;
    let a5_opp = base_opp_score;

    let scores_hero = [base_hero_score, a1_hero, a2_hero, a3_hero, a4_hero, a5_hero];
    let scores_opp = [base_opp_score, a1_opp, a2_opp, a3_opp, a4_opp, a5_opp];

    let mut margin_deltas = [0.0; 6];
    let mut best_a = 0;
    let mut max_margin_gain = 0.0;

    for i in 0..6 {
        let cand_margin = scores_hero[i] - scores_opp[i];
        let d_margin = cand_margin - base_margin;
        margin_deltas[i] = d_margin;
        if d_margin > max_margin_gain + 50.0 {
            max_margin_gain = d_margin;
            best_a = i;
        }
    }

    CompetitiveSample {
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
        base_hero: base_hero_score,
        base_opp: base_opp_score,
        base_margin,
        scores_hero,
        scores_opp,
        margin_deltas,
        best_competitive_a: best_a,
        max_margin_gain,
    }
}

fn main() {
    println!("=========================================================================================");
    println!("     EXP200 — COMPETITIVE MARGIN DATASET MINER & 4-QUADRANT DIAGNOSTIC ENGINE            ");
    println!("=========================================================================================");

    let num_seeds = 5000; // 5,000 seeds x 2 opponents (Adaptive & D.1) = 10,000 matches (60,000 rollouts)
    let base_seed = 200000;

    let mut tasks = Vec::with_capacity(num_seeds * 2);
    for s in 0..num_seeds {
        tasks.push((base_seed + s as u64, 0)); // vs Adaptive Peak
        tasks.push((base_seed + 10000 + s as u64, 1)); // vs D.1 GM
    }

    let t0 = Instant::now();
    println!("Mining 10,000 2-player competitive matches across 6 macro actions (60,000 rollouts)...");

    let samples: Vec<CompetitiveSample> = tasks.into_par_iter().map(|(s, opp)| {
        evaluate_competitive_seed(s, opp)
    }).collect();

    let elapsed = t0.elapsed().as_secs_f64();
    println!("Competitive mining completed in {:.2}s ({:.1} rollouts/sec)\n", elapsed, 60000.0 / elapsed);

    let csv_path = r"D:\kaggriculture\data\exp200_competitive_dataset.csv";
    let mut file = File::create(csv_path).expect("Failed to create CSV");
    writeln!(file, "seed,opp_type,p_milk,cash,cows,sheep,shed_wheat,hands,quads,day,unwatered,mature,opp_cash,opp_cows,opp_sheep,opp_quads,opp_workers,opp_straws,base_hero,base_opp,base_margin,h_a0,h_a1,h_a2,h_a3,h_a4,h_a5,o_a0,o_a1,o_a2,o_a3,o_a4,o_a5,d_m0,d_m1,d_m2,d_m3,d_m4,d_m5,best_a,max_margin_gain").unwrap();

    // 4-Quadrant Diagnostic Counters
    let mut q1_true_alpha = 0;      // solo > 0 & margin > 0
    let mut q2_competitive_trap = 0; // solo > 0 & margin <= 0 (THE FATAL TRAP!)
    let mut q3_harmful = 0;         // solo <= 0 & margin <= 0
    let mut q4_denial_alpha = 0;    // solo <= 0 & margin > 0

    let mut q1_margin_sum = 0.0;
    let mut q2_margin_loss = 0.0;

    let mut optimal_action_counts = [0; 6];
    let mut optimal_margin_gains = [0.0; 6];

    for s in &samples {
        optimal_action_counts[s.best_competitive_a] += 1;
        optimal_margin_gains[s.best_competitive_a] += s.max_margin_gain;

        // Check candidate interventions (a1..a4) vs baseline a0
        for act in 1..=4 {
            let solo_delta = s.scores_hero[act] - s.base_hero;
            let margin_delta = s.margin_deltas[act];

            if solo_delta > 100.0 && margin_delta > 100.0 {
                q1_true_alpha += 1;
                q1_margin_sum += margin_delta;
            } else if solo_delta > 100.0 && margin_delta <= 100.0 {
                q2_competitive_trap += 1;
                q2_margin_loss += margin_delta;
            } else if solo_delta <= 100.0 && margin_delta <= 100.0 {
                q3_harmful += 1;
            } else if solo_delta <= 100.0 && margin_delta > 100.0 {
                q4_denial_alpha += 1;
            }
        }

        writeln!(file, "{},{},{:.2},{:.2},{},{},{},{},{},{},{},{},{:.2},{},{},{},{},{},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{:.1},{},{:.1}",
            s.seed, s.opp_type, s.p_milk, s.cash, s.cows, s.sheep, s.shed_wheat, s.hands, s.quads, s.day,
            s.unwatered, s.mature,
            s.opp_cash, s.opp_cows, s.opp_sheep, s.opp_quads, s.opp_workers, s.opp_straws,
            s.base_hero, s.base_opp, s.base_margin,
            s.scores_hero[0], s.scores_hero[1], s.scores_hero[2], s.scores_hero[3], s.scores_hero[4], s.scores_hero[5],
            s.scores_opp[0], s.scores_opp[1], s.scores_opp[2], s.scores_opp[3], s.scores_opp[4], s.scores_opp[5],
            s.margin_deltas[0], s.margin_deltas[1], s.margin_deltas[2], s.margin_deltas[3], s.margin_deltas[4], s.margin_deltas[5],
            s.best_competitive_a, s.max_margin_gain).unwrap();
    }

    let total_interventions_tested = (samples.len() * 4) as f64;

    println!("=========================================================================================");
    println!("                           4-QUADRANT COMPETITIVE BREAKDOWN                              ");
    println!("=========================================================================================");
    println!("Q1: True Competitive Alpha (Solo > 0 & Margin > 0)    : {:>6} ({:>4.1}%) | Avg Margin Gain: +${:<7.1}",
        q1_true_alpha, (q1_true_alpha as f64 / total_interventions_tested) * 100.0, if q1_true_alpha > 0 { q1_margin_sum / q1_true_alpha as f64 } else { 0.0 });
    println!("Q2: The Competitive Trap   (Solo > 0 & Margin <= 0)   : {:>6} ({:>4.1}%) | Avg Margin Loss:  ${:<7.1} 🚨",
        q2_competitive_trap, (q2_competitive_trap as f64 / total_interventions_tested) * 100.0, if q2_competitive_trap > 0 { q2_margin_loss / q2_competitive_trap as f64 } else { 0.0 });
    println!("Q3: Harmful Interventions  (Solo <= 0 & Margin <= 0)  : {:>6} ({:>4.1}%)",
        q3_harmful, (q3_harmful as f64 / total_interventions_tested) * 100.0);
    println!("Q4: Denial / Spite Alpha   (Solo <= 0 & Margin > 0)   : {:>6} ({:>4.1}%)",
        q4_denial_alpha, (q4_denial_alpha as f64 / total_interventions_tested) * 100.0);
    println!("-----------------------------------------------------------------------------------------");
    println!("=========================================================================================");
    println!("                      COMPETITIVE MARGIN-OPTIMAL ACTION SUMMARY                          ");
    println!("=========================================================================================");
    let act_names = [
        "a0: Default Adaptive",
        "a1: Buy Wheat (Day 0)",
        "a2: Hire 1 (Day 6)",
        "a3: 1 Sheep (Day 8)",
        "a4: 2 Sheep (Day 8)",
        "a5: 4 Sheep (Day 8)",
    ];
    for i in 0..6 {
        let cnt = optimal_action_counts[i];
        let pct = (cnt as f64 / samples.len() as f64) * 100.0;
        let avg_g = if cnt > 0 { optimal_margin_gains[i] / cnt as f64 } else { 0.0 };
        println!("{:<28} | Optimal Margin in {:>5} matches ({:>4.1}%) | Avg Margin Gain: +${:<7.1}",
            act_names[i], cnt, pct, avg_g);
    }
    println!("=========================================================================================");
    println!("Saved complete competitive dataset to {}", csv_path);
}

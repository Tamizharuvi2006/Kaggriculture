//! EXP187 — Empirical Verification of Biological State Invariants on 10,000 Held-Out Seeds.
//! Rigorously evaluates Precision, Recall, False Positives, False Negatives, and Rescue Gain (Δ$).

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};
use fastsim::market::{Product, MarketOrder};
use fastsim::farm::{Crop, Animal, Tile};
use rayon::prelude::*;
use std::time::Instant;

#[derive(Default, Clone)]
pub struct InvariantAuditResult {
    pub seed: u64,
    pub baseline_reward: f64,
    pub is_true_stall: bool, // Final reward < $50,000

    // Feed Invariant (Days 0-3)
    pub feed_detector_fired: bool,
    pub feed_detector_step: usize,
    pub feed_rescue_reward: f64,

    // Labor Invariant (Days 4-7)
    pub labor_detector_fired: bool,
    pub labor_detector_step: usize,
    pub labor_rescue_reward: f64,
}

pub fn audit_seed(seed: u64) -> InvariantAuditResult {
    let base_policy = AdaptiveTerminalPolicy::new();
    let opp_policy = AdaptiveTerminalPolicy::new();

    // 1. Run baseline episode to establish ground truth
    let mut base_state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let mut state_snapshots: Vec<(usize, GameState)> = Vec::new();

    while !base_state.done {
        let step = base_state.step;
        if step < 192 && step % 24 == 0 { // Check at Hour 0 of Days 0..7
            state_snapshots.push((step, base_state.clone()));
        }
        let a0 = base_policy.act(&base_state, 0);
        let a1 = opp_policy.act(&base_state, 1);
        step_game(&mut base_state, &[a0, a1]);
    }

    let baseline_reward = base_state.farms[0].money;
    let is_true_stall = baseline_reward < 50000.0;

    let mut res = InvariantAuditResult {
        seed,
        baseline_reward,
        is_true_stall,
        ..Default::default()
    };

    // 2. Audit Invariants on early-game snapshots
    for (step, st) in state_snapshots {
        let day = st.day;
        let farm = &st.farms[0];
        let priv_farm = &st.privates[0];

        let mut num_cows = 0;
        let mut growing_wheat = 0;
        let mut total_crops = 0;
        let mut unwatered_crops = 0;

        for row in &farm.tiles {
            for tile in row {
                match tile {
                    Tile::Animal(a) if a.animal == Animal::Cow => num_cows += 1,
                    Tile::Plant(p) => {
                        total_crops += 1;
                        if p.crop == Crop::Wheat { growing_wheat += 1; }
                        if !p.watered_today { unwatered_crops += 1; }
                    }

                    _ => {}
                }
            }
        }

        let shed_wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0);
        let hands = farm.hands.len();
        let money = farm.money;

        // INVARIANT 1: Feed Starvation (Days 0-3)
        // Cow exists, zero wheat in shed, and zero wheat plants currently growing
        if !res.feed_detector_fired && day <= 3 {
            let feed_starvation = (num_cows > 0 && shed_wheat == 0 && growing_wheat == 0)
                || (day == 0 && shed_wheat < 2 && growing_wheat == 0);

            if feed_starvation {
                res.feed_detector_fired = true;
                res.feed_detector_step = step;

                // Run counterfactual rescue rollout: BUY_SEED_WHEAT_4
                let mut rescue_st = st.clone();
                let mut rescue_act = base_policy.act(&rescue_st, 0);
                rescue_act.market.push(MarketOrder::BuySeed(Crop::Wheat, 4));
                let opp_act = opp_policy.act(&rescue_st, 1);
                step_game(&mut rescue_st, &[rescue_act, opp_act]);

                while !rescue_st.done {
                    let a0 = base_policy.act(&rescue_st, 0);
                    let a1 = opp_policy.act(&rescue_st, 1);
                    step_game(&mut rescue_st, &[a0, a1]);
                }
                res.feed_rescue_reward = rescue_st.farms[0].money;
            }
        }

        // INVARIANT 2: Labor Starvation / Rot Bottleneck (Days 4-7)
        // High crop volume, insufficient workers to water/maintain, and sufficient capital to hire
        if !res.labor_detector_fired && (4..=7).contains(&day) {
            let labor_starvation = total_crops >= 15 && hands < 2 && unwatered_crops >= 8 && money >= 100.0;

            if labor_starvation {
                res.labor_detector_fired = true;
                res.labor_detector_step = step;

                // Run counterfactual rescue rollout: HIRE_2
                let mut rescue_st = st.clone();
                let mut rescue_act = base_policy.act(&rescue_st, 0);
                rescue_act.market.push(MarketOrder::Hire);
                rescue_act.market.push(MarketOrder::Hire);
                let opp_act = opp_policy.act(&rescue_st, 1);
                step_game(&mut rescue_st, &[rescue_act, opp_act]);

                while !rescue_st.done {
                    let a0 = base_policy.act(&rescue_st, 0);
                    let a1 = opp_policy.act(&rescue_st, 1);
                    step_game(&mut rescue_st, &[a0, a1]);
                }
                res.labor_rescue_reward = rescue_st.farms[0].money;
            }
        }
    }

    res
}

fn main() {
    println!("=========================================================================================");
    println!("       EXP187 — EMPIRICAL VERIFICATION OF BIOLOGICAL INVARIANTS (10,000 HELD-OUT SEEDS)   ");
    println!("=========================================================================================");

    let seeds: Vec<u64> = (20000..30000).collect(); // 10,000 completely fresh held-out seeds
    let t0 = Instant::now();

    println!("Auditing 10,000 full game trajectories and counterfactual rescue rollouts...");
    let results: Vec<InvariantAuditResult> = seeds.par_iter().map(|&s| audit_seed(s)).collect();
    let elapsed = t0.elapsed().as_secs_f64();

    let total_seeds = results.len();
    let total_stalls = results.iter().filter(|r| r.is_true_stall).count();
    let stall_rate = (total_stalls as f64 / total_seeds as f64) * 100.0;

    println!("\nAudit Completed in {:.2}s ({:.1} trajectories/sec)", elapsed, total_seeds as f64 / elapsed);
    println!("Total Held-Out Seeds           : {}", total_seeds);
    println!("True Stall Trajectories (< $50k): {} ({:.2}%)\n", total_stalls, stall_rate);

    // =========================================================================
    // 1. INVARIANT 1 AUDIT: FEED STARVATION
    // =========================================================================
    let mut feed_tp = 0;
    let mut feed_fp = 0;
    let mut feed_fn = 0;
    let mut feed_gains = Vec::new();

    for r in &results {
        if r.feed_detector_fired && r.is_true_stall {
            feed_tp += 1;
            feed_gains.push(r.feed_rescue_reward - r.baseline_reward);
        } else if r.feed_detector_fired && !r.is_true_stall {
            feed_fp += 1;
            feed_gains.push(r.feed_rescue_reward - r.baseline_reward);
        } else if !r.feed_detector_fired && r.is_true_stall {
            feed_fn += 1;
        }
    }

    let feed_precision = (feed_tp as f64 / (feed_tp + feed_fp).max(1) as f64) * 100.0;
    let feed_recall = (feed_tp as f64 / (feed_tp + feed_fn).max(1) as f64) * 100.0;
    let feed_mean_gain = if !feed_gains.is_empty() { feed_gains.iter().sum::<f64>() / feed_gains.len() as f64 } else { 0.0 };

    println!("-----------------------------------------------------------------------------------------");
    println!("INVARIANT 1: FEED STARVATION DETECTOR (Days 0–3: num_cows > 0 && shed_wheat == 0 && growing_wheat == 0)");
    println!("-----------------------------------------------------------------------------------------");
    println!("Total Times Fired              : {}", feed_tp + feed_fp);
    println!("True Positives (True Stalls)   : {} (Precision: {:.1}%)", feed_tp, feed_precision);
    println!("False Positives (Healthy Farms): {} ({:.1}%)", feed_fp, (feed_fp as f64 / (feed_tp + feed_fp).max(1) as f64) * 100.0);
    println!("False Negatives (Missed Stalls): {} (Recall: {:.1}%)", feed_fn, feed_recall);
    println!("Mean Rescue EV (Δ$)            : {:+.1}", feed_mean_gain);
    if !feed_gains.is_empty() {
        let max_gain = feed_gains.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let min_gain = feed_gains.iter().cloned().fold(f64::INFINITY, f64::min);
        println!("Max Rescue Gain                : +${:.1} | Worst Rescue Loss: {:+.1}", max_gain, min_gain);
    }
    println!();

    // =========================================================================
    // 2. INVARIANT 2 AUDIT: LABOR BOTTLENECK
    // =========================================================================
    let mut labor_tp = 0;
    let mut labor_fp = 0;
    let mut labor_fn = 0;
    let mut labor_gains = Vec::new();

    for r in &results {
        if r.labor_detector_fired && r.is_true_stall {
            labor_tp += 1;
            labor_gains.push(r.labor_rescue_reward - r.baseline_reward);
        } else if r.labor_detector_fired && !r.is_true_stall {
            labor_fp += 1;
            labor_gains.push(r.labor_rescue_reward - r.baseline_reward);
        } else if !r.labor_detector_fired && r.is_true_stall {
            labor_fn += 1;
        }
    }

    let labor_precision = (labor_tp as f64 / (labor_tp + labor_fp).max(1) as f64) * 100.0;
    let labor_recall = (labor_tp as f64 / (labor_tp + labor_fn).max(1) as f64) * 100.0;
    let labor_mean_gain = if !labor_gains.is_empty() { labor_gains.iter().sum::<f64>() / labor_gains.len() as f64 } else { 0.0 };

    println!("-----------------------------------------------------------------------------------------");
    println!("INVARIANT 2: LABOR STARVATION DETECTOR (Days 4–7: crops >= 15 && hands < 2 && unwatered >= 8)");
    println!("-----------------------------------------------------------------------------------------");
    println!("Total Times Fired              : {}", labor_tp + labor_fp);
    println!("True Positives (True Stalls)   : {} (Precision: {:.1}%)", labor_tp, labor_precision);
    println!("False Positives (Healthy Farms): {} ({:.1}%)", labor_fp, (labor_fp as f64 / (labor_tp + labor_fp).max(1) as f64) * 100.0);
    println!("False Negatives (Missed Stalls): {} (Recall: {:.1}%)", labor_fn, labor_recall);
    println!("Mean Rescue EV (Δ$)            : {:+.1}", labor_mean_gain);
    if !labor_gains.is_empty() {
        let max_gain = labor_gains.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let min_gain = labor_gains.iter().cloned().fold(f64::INFINITY, f64::min);
        println!("Max Rescue Gain                : +${:.1} | Worst Rescue Loss: {:+.1}", max_gain, min_gain);
    }
    println!("=========================================================================================");
}

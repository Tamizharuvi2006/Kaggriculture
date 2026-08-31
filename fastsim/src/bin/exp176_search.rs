//! EXP176 — FastSim Elite Livestock Architecture Search Harness.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};
use fastsim::market::{Product, MarketOrder};
use fastsim::farm::{Animal, Tile};
use rayon::prelude::*;
use std::time::Instant;

#[derive(Clone, Debug)]
pub struct LivestockArm {
    pub name: &'static str,
    pub target_cows: usize,
    pub target_sheep: usize,
    pub purchase_step: usize,
}

#[derive(Clone, Debug, Default)]
pub struct TrajectoryMetrics {
    pub name: String,
    pub target_cows: usize,
    pub target_sheep: usize,
    pub purchase_step: usize,
    pub total_matches: usize,
    pub wins: usize,
    pub ties: usize,
    pub losses: usize,
    pub mean_reward: f64,
    pub control_mean_reward: f64,
    pub delta_margin: f64,
    
    // Day checkpoints (Days 1, 3, 5, 7, 10, 15, 20, 25, 29, 30)
    pub cash_by_day: [f64; 10],
    pub min_runway_cash: f64,
}

/// A policy that wraps AdaptiveTerminal / D.1 but injects a livestock schedule
pub struct LivestockPolicy {
    base: AdaptiveTerminalPolicy,
    target_cows: usize,
    target_sheep: usize,
    purchase_step: usize,
}

impl LivestockPolicy {
    pub fn new(target_cows: usize, target_sheep: usize, purchase_step: usize) -> Self {
        Self {
            base: AdaptiveTerminalPolicy::new(),
            target_cows,
            target_sheep,
            purchase_step,
        }
    }
}

impl Policy for LivestockPolicy {
    fn name(&self) -> &'static str {
        "livestock_arm"
    }

    fn act(&self, state: &GameState, player_idx: usize) -> fastsim::engine::step::PlayerAction {
        let mut act = self.base.act(state, player_idx);
        let step = state.step;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];

        if step >= self.purchase_step {
            // Count current live animals
            let mut cows = 0;
            let mut sheep = 0;
            for row in &farm.tiles {
                for tile in row {
                    if let Tile::Animal(a) = tile {
                        if a.animal.name() == "COW" { cows += 1; }
                        else if a.animal.name() == "SHEEP" { sheep += 1; }
                    }
                }
            }

            let cows_in_shed = *priv_farm.shed.get("COW").unwrap_or(&0) as usize;
            let sheep_in_shed = *priv_farm.shed.get("SHEEP").unwrap_or(&0) as usize;

            let money = farm.money;

            // Purchase livestock if below target and cash permits
            if cows + cows_in_shed < self.target_cows && money >= 400.0 {
                let needed = self.target_cows - (cows + cows_in_shed);
                let can_buy = ((money / 400.0).floor() as i64).min(needed as i64).min(2);
                if can_buy > 0 {
                    act.market.push(MarketOrder::BuyAnimal(Animal::Cow, can_buy));
                }
            }

            if sheep + sheep_in_shed < self.target_sheep && money >= 500.0 {
                let needed = self.target_sheep - (sheep + sheep_in_shed);
                let can_buy = ((money / 500.0).floor() as i64).min(needed as i64).min(2);
                if can_buy > 0 {
                    act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, can_buy));
                }
            }

            // Also ensure feed (WHEAT) is purchased if livestock present
            let total_animals = cows + sheep;
            if total_animals > 0 {
                let wheat_in_shed = *priv_farm.shed.get("WHEAT").unwrap_or(&0);
                if wheat_in_shed < (total_animals as i64 * 3) && money >= 50.0 {
                    let buy_n = (total_animals as i64 * 4 - wheat_in_shed).max(2).min(10);
                    act.market.push(MarketOrder::BuyProduct(Product::Wheat, buy_n));
                }
            }
        }

        act
    }
}

pub fn evaluate_arm(
    arm: &LivestockArm,
    seeds: &[u64],
    control_policy: &AdaptiveTerminalPolicy,
) -> TrajectoryMetrics {
    let hero_policy = LivestockPolicy::new(arm.target_cows, arm.target_sheep, arm.purchase_step);
    let mut tasks = Vec::new();
    for &seed in seeds {
        tasks.push((seed, 0));
        tasks.push((seed, 1));
    }

    let results: Vec<(f64, f64, [f64; 10], f64)> = tasks.into_par_iter().map(|(seed, seat)| {
        let opp_seat = 1 - seat;
        
        // 1. Run Control Match
        let mut ctrl_state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !ctrl_state.done && ctrl_state.step < 720 {
            let a_hero = control_policy.act(&ctrl_state, seat);
            let a_opp = control_policy.act(&ctrl_state, opp_seat);
            let actions = if seat == 0 { [a_hero, a_opp] } else { [a_opp, a_hero] };
            step_game(&mut ctrl_state, &actions);
        }
        let ctrl_reward = ctrl_state.farms[seat].money;

        // 2. Run Livestock Arm Match
        let mut arm_state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        let mut day_cash = [0.0; 10];
        let day_checkpoints = [1, 3, 5, 7, 10, 15, 20, 25, 29, 30];
        let mut min_cash: f64 = 3000.0;
        
        while !arm_state.done && arm_state.step < 720 {
            let day = arm_state.day;
            let cash = arm_state.farms[seat].money;
            min_cash = min_cash.min(cash);

            for (idx, &cp_day) in day_checkpoints.iter().enumerate() {
                if day == cp_day && arm_state.hour == 0 {
                    day_cash[idx] = cash;
                }
            }

            let a_hero = hero_policy.act(&arm_state, seat);
            let a_opp = control_policy.act(&arm_state, opp_seat);
            let actions = if seat == 0 { [a_hero, a_opp] } else { [a_opp, a_hero] };
            step_game(&mut arm_state, &actions);
        }
        let arm_reward = arm_state.farms[seat].money;

        (arm_reward, ctrl_reward, day_cash, min_cash)
    }).collect();

    let total = results.len();
    let mut wins = 0;
    let mut ties = 0;
    let mut losses = 0;
    let mut sum_arm_reward = 0.0;
    let mut sum_ctrl_reward = 0.0;
    let mut avg_day_cash = [0.0; 10];
    let mut avg_min_cash = 0.0;

    for (arm_r, ctrl_r, dc, mc) in &results {
        sum_arm_reward += arm_r;
        sum_ctrl_reward += ctrl_r;
        avg_min_cash += mc;
        for i in 0..10 {
            avg_day_cash[i] += dc[i];
        }

        if *arm_r > *ctrl_r + 1.0 {
            wins += 1;
        } else if *ctrl_r > *arm_r + 1.0 {
            losses += 1;
        } else {
            ties += 1;
        }
    }

    let mean_reward = sum_arm_reward / total as f64;
    let control_mean_reward = sum_ctrl_reward / total as f64;

    for i in 0..10 {
        avg_day_cash[i] /= total as f64;
    }

    TrajectoryMetrics {
        name: arm.name.to_string(),
        target_cows: arm.target_cows,
        target_sheep: arm.target_sheep,
        purchase_step: arm.purchase_step,
        total_matches: total,
        wins,
        ties,
        losses,
        mean_reward,
        control_mean_reward,
        delta_margin: mean_reward - control_mean_reward,
        cash_by_day: avg_day_cash,
        min_runway_cash: avg_min_cash / total as f64,
    }
}

fn main() {
    println!("================================================================================");
    println!("EXP176 — FASTSIM ELITE LIVESTOCK ARCHITECTURE SEARCH (SCREENING SWEEP)");
    println!("================================================================================");

    let configurations = [
        ("4C/0S", 4, 0),
        ("4C/1S", 4, 1),
        ("4C/2S", 4, 2),
        ("6C/2S", 6, 2),
        ("6C/4S", 6, 4),
        ("8C/4S", 8, 4),
        ("8C/6S", 8, 6),
    ];

    let purchase_steps = [4, 6, 12, 24, 48, 72, 120, 168, 240];

    let mut arms = Vec::new();
    for &(name, c, s) in &configurations {
        for &step in &purchase_steps {
            arms.push(LivestockArm {
                name,
                target_cows: c,
                target_sheep: s,
                purchase_step: step,
            });
        }
    }

    let control_policy = AdaptiveTerminalPolicy::new();
    let sweep_seeds: Vec<u64> = (1000..1100).collect(); // 100 seeds x 2 seats = 200 matches per arm

    println!("Evaluating {} arms across {} paired matches each...", arms.len(), sweep_seeds.len() * 2);
    let t0 = Instant::now();

    let mut metrics_list: Vec<TrajectoryMetrics> = Vec::new();
    for (idx, arm) in arms.iter().enumerate() {
        let m = evaluate_arm(arm, &sweep_seeds, &control_policy);
        println!(
            "[{:2}/{}] Arm: {:5} @ Step {:3} | WR: {:5.1}% | Reward: ${:7.0} vs Ctrl ${:7.0} (Delta: {:+6.0}) | MinCash: ${:5.0}",
            idx + 1,
            arms.len(),
            m.name,
            m.purchase_step,
            (m.wins as f64 / m.total_matches as f64) * 100.0,
            m.mean_reward,
            m.control_mean_reward,
            m.delta_margin,
            m.min_runway_cash
        );
        metrics_list.push(m);
    }

    let elapsed = t0.elapsed().as_secs_f64();
    println!("Sweep completed in {:.2}s ({:.1} total matches/sec)!", elapsed, (arms.len() * sweep_seeds.len() * 4) as f64 / elapsed);

    // Sort by Delta Margin
    metrics_list.sort_by(|a, b| b.delta_margin.partial_cmp(&a.delta_margin).unwrap());

    println!("\n================================================================================");
    println!("TOP 10 LIVESTOCK TRAJECTORIES RANKED BY DELTA REWARD VS CONTROL:");
    println!("================================================================================");
    for (rank, m) in metrics_list.iter().take(10).enumerate() {
        println!(
            "#{}: Arm {:5} @ Step {:3} | WR: {:5.1}% | Mean: ${:.1} | Delta: {:+7.1} | Min Runway: ${:.0}",
            rank + 1,
            m.name,
            m.purchase_step,
            (m.wins as f64 / m.total_matches as f64) * 100.0,
            m.mean_reward,
            m.delta_margin,
            m.min_runway_cash
        );
        println!(
            "    Cash Runway: D1=${:.0}, D3=${:.0}, D5=${:.0}, D7=${:.0}, D10=${:.0}, D15=${:.0}, D20=${:.0}, D25=${:.0}",
            m.cash_by_day[0], m.cash_by_day[1], m.cash_by_day[2], m.cash_by_day[3],
            m.cash_by_day[4], m.cash_by_day[5], m.cash_by_day[6], m.cash_by_day[7]
        );
    }
}

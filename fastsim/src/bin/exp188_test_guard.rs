//! EXP188 — Verification of Day 8 Liquidity Guard on Seed 1001.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};
use fastsim::market::MarketOrder;

fn main() {
    println!("================================================================================");
    println!("TESTING DAY 8 LIQUIDITY GUARD ON SEED 1001 (PREVIOUSLY $35,988)");
    println!("================================================================================");

    let base_policy = AdaptiveTerminalPolicy::new();
    let opp_policy = AdaptiveTerminalPolicy::new();

    // 1. Untouched baseline on Seed 1001
    let mut st_base = GameState::new(1001, 10, 3000.0, 720, 24, 100);
    while !st_base.done {
        let a0 = base_policy.act(&st_base, 0);
        let a1 = opp_policy.act(&st_base, 1);
        step_game(&mut st_base, &[a0, a1]);
    }
    println!("Untouched Baseline Score on Seed 1001 : ${:.1}", st_base.farms[0].money);

    // 2. Baseline with Day 8 Liquidity Guard (reject animal buy if post_cash < $800)
    let mut st_guard = GameState::new(1001, 10, 3000.0, 720, 24, 100);
    let mut sheep_cancelled = 0;

    while !st_guard.done {
        let day = st_guard.day;
        let mut a0 = base_policy.act(&st_guard, 0);

        if day == 8 {
            let money = st_guard.farms[0].money;
            let initial_orders = a0.market.clone();
            a0.market.retain(|order| {
                if let MarketOrder::BuyAnimal(animal, count) = order {
                    let cost = match animal {
                        fastsim::farm::Animal::Cow => 800.0 * (*count as f64),
                        fastsim::farm::Animal::Sheep => 600.0 * (*count as f64),
                        _ => 0.0,
                    };
                    if money - cost < 800.0 {
                        sheep_cancelled += *count;
                        false // REJECT ORDER
                    } else {
                        true
                    }
                } else {
                    true
                }
            });
        }

        let a1 = opp_policy.act(&st_guard, 1);
        step_game(&mut st_guard, &[a0, a1]);
    }

    println!("Protected Score on Seed 1001 (Guarded): ${:.1} (Cancelled {} sheep)", st_guard.farms[0].money, sheep_cancelled);
    println!("Net Single-Seed Rescue Improvement   : {:+.1}", st_guard.farms[0].money - st_base.farms[0].money);
    println!("================================================================================");
}

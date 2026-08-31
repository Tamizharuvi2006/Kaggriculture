//! EXP187 — Day 8-9 Forensic Audit: Hour-by-Hour log of Seed 1001 vs Seed 1000.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};
use fastsim::market::Product;

fn main() {
    println!("================================================================================");
    println!("EXP187 — DAY 8-9 FORENSIC AUDIT: SEED 1001 (STALL) vs SEED 1000 (HEALTHY)");
    println!("================================================================================");

    let base_policy = AdaptiveTerminalPolicy::new();
    let opp_policy = AdaptiveTerminalPolicy::new();

    for &seed in &[1001, 1000] {
        let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        println!("\n--- SEED {} ---", seed);

        while !st.done {
            let day = st.day;
            let hour = st.hour;
            let step = st.step;

            if day >= 7 && day <= 10 {
                let farm = &st.farms[0];
                let priv_farm = &st.privates[0];
                let p_milk = *st.market.prices.get(&Product::Milk).unwrap_or(&160);
                let p_straw = *st.market.prices.get(&Product::Strawberry).unwrap_or(&120);

                let a0 = base_policy.act(&st, 0);
                if !a0.market.is_empty() || hour == 0 {
                    println!("Day {:2} Hr {:2} (Step {:3}) | Cash: ${:6.0} | Shed Milk: {} (p=${}) | Shed Straw: {} (p=${}) | Orders: {:?}",
                        day, hour, step, farm.money, priv_farm.shed.get("MILK").unwrap_or(&0), p_milk,
                        priv_farm.shed.get("STRAWBERRY").unwrap_or(&0), p_straw, a0.market);
                }
                let a1 = opp_policy.act(&st, 1);
                step_game(&mut st, &[a0, a1]);
            } else {
                let a0 = base_policy.act(&st, 0);
                let a1 = opp_policy.act(&st, 1);
                step_game(&mut st, &[a0, a1]);
            }
        }
    }
}

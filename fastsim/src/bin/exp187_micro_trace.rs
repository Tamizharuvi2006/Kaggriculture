//! EXP187 — Micro-Step Diagnostic: Step-by-Step Log of Days 5..10 on Seed 20002 (Stall) vs Seed 20000 (Healthy).

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};
use fastsim::farm::{Crop, Animal, Tile};

fn trace_game(seed: u64, label: &str) {
    println!("\n================================================================================");
    println!("TRACE OF {} (SEED {})", label, seed);
    println!("================================================================================");

    let base_policy = AdaptiveTerminalPolicy::new();
    let opp_policy = AdaptiveTerminalPolicy::new();
    let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);

    while !st.done {
        let day = st.day;
        let hour = st.hour;
        let step = st.step;

        if (0..=20).contains(&day) && hour == 0 {
            let farm = &st.farms[0];
            let priv_farm = &st.privates[0];
            let mut melon_plants = 0;
            let mut straw_plants = 0;

            for row in &farm.tiles {
                for tile in row {
                    if let Tile::Plant(p) = tile {
                        if p.crop == Crop::Melon { melon_plants += 1; }
                        if p.crop == Crop::Strawberry { straw_plants += 1; }
                    }
                }
            }

            println!("Day {:2} (Step {:3}) | Cash: ${:7.1} | Quads: {} | Hands: {} | Melons: {} | Straws: {} | Shed (Straw: {}, Milk: {})",
                day, step, farm.money, farm.unlocked_quadrants.len(), farm.hands.len(), melon_plants, straw_plants,
                priv_farm.shed.get("STRAWBERRY").unwrap_or(&0), priv_farm.shed.get("MILK").unwrap_or(&0));
        }

        let a0 = base_policy.act(&st, 0);
        let a1 = opp_policy.act(&st, 1);
        step_game(&mut st, &[a0, a1]);
    }

    println!("FINAL SCORE: ${:.1}", st.farms[0].money);
}

fn main() {
    trace_game(1001, "STALL SEED (1001)");
    trace_game(1000, "HEALTHY SEED (1000)");
}


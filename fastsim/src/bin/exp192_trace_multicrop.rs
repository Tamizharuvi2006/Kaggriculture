//! Diagnostic trace of MultiCropPlannerPolicy on Seed 70000.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, MultiCropPlannerPolicy, AdaptiveTerminalPolicy};

fn main() {
    let hero = MultiCropPlannerPolicy::new();
    let opp = AdaptiveTerminalPolicy::new();
    let mut st = GameState::new(70000, 10, 3000.0, 720, 24, 100);

    println!("=== TRACING MULTICROP PLANNER (HERO) vs ADAPTIVE (OPP) ===");
    while !st.done {
        let day = st.day;
        let hour = st.hour;
        let step = st.step;

        if hour == 0 {
            println!("Day {:2} (Step {:3}) | Hero Money: ${:6.1} (Hands: {}) | Opp Money: ${:6.1}",
                day, step, st.farms[0].money, st.farms[0].hands.len(), st.farms[1].money);
        }

        let a0 = hero.act(&st, 0);
        let a1 = opp.act(&st, 1);
        step_game(&mut st, &[a0, a1]);
    }

    println!("FINAL: Hero Money: ${:.1} | Opp Money: ${:.1}", st.farms[0].money, st.farms[1].money);
}

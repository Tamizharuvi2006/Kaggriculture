//! EXP192 — Audit MultiCropPlanner on Day 4-6.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, MultiCropPlannerPolicy, AdaptiveTerminalPolicy};

fn main() {
    let hero = MultiCropPlannerPolicy::new();
    let opp = AdaptiveTerminalPolicy::new();
    let mut st = GameState::new(70000, 10, 3000.0, 720, 24, 100);

    while !st.done {
        let day = st.day;
        let hour = st.hour;
        let step = st.step;

        let a0 = hero.act(&st, 0);
        if (4..=6).contains(&day) && !a0.market.is_empty() {
            println!("Day {:2} Hr {:2} (Step {:3}) | Cash: ${:6.1} | Orders: {:?}",
                day, hour, step, st.farms[0].money, a0.market);
        }
        let a1 = opp.act(&st, 1);
        step_game(&mut st, &[a0, a1]);
    }
}

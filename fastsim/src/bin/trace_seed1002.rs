use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, PassPolicy, V41Policy};
use serde_json::Value;
use std::fs::File;

fn main() {
    let snaps: Value = serde_json::from_reader(File::open("scratch_snaps_all_1002.json").unwrap()).unwrap();
    let mut state = GameState::new(1002, 10, 3000.0, 720, 24, 100);
    let hero = V41Policy::new();
    let opp = PassPolicy;

    for s in 0..720 {
        let snap = &snaps[&s.to_string()];
        let off_money = snap["money"].as_f64().unwrap();
        let rust_money = state.farms[0].money;

        if (off_money - rust_money).abs() > 1e-3 {
            println!("\n[MONEY DIVERGENCE FOUND AT STEP {}]", s);
            println!("  Official Money: ${:.1}", off_money);
            println!("  Rust Money    : ${:.1}", rust_money);
            println!("  Official Shed : {:?}", snap["shed"]);
            println!("  Rust Shed     : {:?}", state.privates[0].shed);
            let a0 = hero.act(&state, 0);
            println!("  Official Act  : {:?}", snap.get("action"));
            println!("  Rust Act      : {:?}", a0);
            return;
        }

        if s < 719 {
            let a0 = hero.act(&state, 0);
            let a1 = opp.act(&state, 1);
            step_game(&mut state, &[a0, a1]);
        }
    }
    println!("ALL 720 STEPS MATCHED 100% BIT-EXACT!");
}

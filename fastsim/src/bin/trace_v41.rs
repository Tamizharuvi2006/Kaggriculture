use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, PassPolicy, V41Policy};

fn main() {
    let mut state = GameState::new(1000, 10, 3000.0, 720, 24, 100);
    let hero = V41Policy::new();
    let opp = PassPolicy;

    for s in 0..73 {
        let a_opp = opp.act(&state, 0);
        let a_hero = hero.act(&state, 1);

        if s >= 70 {
            println!("Step {:3} | Rust Seat 1 Money: ${:.1} | Action: {:?}",
                s, state.farms[1].money, a_hero);
        }

        step_game(&mut state, &[a_opp, a_hero]);
    }
}

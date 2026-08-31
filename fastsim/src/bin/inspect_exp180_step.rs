//! Inspect steps 260..360 for TargetDispatcherPolicy.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{AdaptiveTerminalPolicy, TargetDispatcherPolicy, Policy};
use fastsim::farm::Tile;

fn main() {
    let hero = TargetDispatcherPolicy::new();
    let control = AdaptiveTerminalPolicy::new();
    let mut state = GameState::new(1000, 10, 3000.0, 720, 24, 100);

    for s in 0..360 {
        let a_hero = hero.act(&state, 0);
        let a_opp = control.act(&state, 1);
        
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[0];
        let priv_farm = &state.privates[0];
        
        // Count plants and animals
        let mut plant_count = 0;
        let mut mature_count = 0;
        let mut watered_count = 0;
        for row in &farm.tiles {
            for t in row {
                if let Tile::Plant(p) = t {
                    plant_count += 1;
                    if p.yield_units > 0 { mature_count += 1; }
                    if p.watered_today { watered_count += 1; }
                }
            }
        }
        
        if (260..290).contains(&s) || s % 24 == 0 {
            println!("Step {:3} (D{:2}:H{:2}) | Cash: ${:.1} | Shed: {:?} | Plants: {:2} (W:{:2}, M:{:2}) | Farmer: {:?} pos:{:?} | Hands({}): {:?} | Market: {:?}",
                s, day, hour, farm.money, priv_farm.shed, plant_count, watered_count, mature_count,
                a_hero.farmer, farm.farmer, farm.hands.len(), a_hero.hands, a_hero.market
            );
        }
        
        step_game(&mut state, &[a_hero, a_opp]);
    }
}

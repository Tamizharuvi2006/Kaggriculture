use fastsim::policies::AdaptiveTerminalPolicy;
use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::Policy;
use fastsim::market::{Product, MarketOrder};
use fastsim::farm::{Animal, Tile};
use rayon::prelude::*;
use std::time::Instant;

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
    fn name(&self) -> &'static str { "livestock" }
    fn act(&self, state: &GameState, player_idx: usize) -> fastsim::engine::step::PlayerAction {
        let mut act = self.base.act(state, player_idx);
        let step = state.step;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];

        if step >= self.purchase_step {
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

fn main() {
    println!("================================================================================");
    println!("EXP176 — 10,000-MATCH PAIRED VALIDATION (TOP 3 TRAJECTORIES VS CONTROL)");
    println!("================================================================================");

    let top_trajectories = [
        ("6C/2S @ Step 240", 6, 2, 240),
        ("4C/0S @ Step 240", 4, 0, 240),
        ("8C/6S @ Step 240", 8, 6, 240),
    ];

    let control = AdaptiveTerminalPolicy::new();
    let seeds: Vec<u64> = (1000..6000).collect(); // 5,000 seeds x 2 seats = 10,000 matches

    for &(name, c, s, step) in &top_trajectories {
        let hero = LivestockPolicy::new(c, s, step);
        let t0 = Instant::now();

        let mut tasks = Vec::new();
        for &seed in &seeds {
            tasks.push((seed, 0));
            tasks.push((seed, 1));
        }

        let results: Vec<(f64, f64)> = tasks.into_par_iter().map(|(seed, seat)| {
            let opp_seat = 1 - seat;
            let mut state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
            while !state.done && state.step < 720 {
                let a_hero = hero.act(&state, seat);
                let a_opp = control.act(&state, opp_seat);
                let actions = if seat == 0 { [a_hero, a_opp] } else { [a_opp, a_hero] };
                step_game(&mut state, &actions);
            }
            (state.farms[seat].money, state.farms[opp_seat].money)
        }).collect();

        let total = results.len();
        let mut wins = 0;
        let mut sum_hero = 0.0;
        let mut sum_ctrl = 0.0;
        for (h, c_r) in &results {
            sum_hero += h;
            sum_ctrl += c_r;
            if *h > *c_r + 1.0 { wins += 1; }
        }

        let elapsed = t0.elapsed().as_secs_f64();
        let mean_hero = sum_hero / total as f64;
        let mean_ctrl = sum_ctrl / total as f64;
        let wr = (wins as f64 / total as f64) * 100.0;

        println!("Arm: {:20} | 10,000 Matches in {:.2}s ({:.1} eps/s) | WR: {:4.1}% | Hero: ${:7.1} vs Ctrl: ${:7.1} | Delta: {:+7.1}",
            name, elapsed, total as f64 / elapsed, wr, mean_hero, mean_ctrl, mean_hero - mean_ctrl
        );
    }
}

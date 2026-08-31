use super::Policy;
use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::farm::{Crop, Tile};
use crate::market::{Product, MarketOrder};
use crate::workers::UnitAction;

pub struct PassPolicy;

impl Policy for PassPolicy {
    fn name(&self) -> &'static str { "pass" }
    fn act(&self, _state: &GameState, _player_idx: usize) -> PlayerAction {
        PlayerAction {
            farmer: UnitAction::Pass,
            hands: Vec::new(),
            market: Vec::new(),
        }
    }
}

pub struct StarterCarrotPolicy;

impl Policy for StarterCarrotPolicy {
    fn name(&self) -> &'static str { "starter" }
    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let farm = &state.farms[player_idx];
        let priv_state = &state.privates[player_idx];
        let (fx, fy) = farm.farmer;
        let tile = &farm.tiles[fy][fx];
        let day = state.day as i32;

        let carrot_seeds = *priv_state.seeds.get(&Crop::Carrot).unwrap_or(&0);
        let carrot_shed = *priv_state.shed.get("CARROT").unwrap_or(&0);

        let mut market = Vec::new();
        if carrot_shed > 0 {
            market.push(MarketOrder::Sell(Product::Carrot, carrot_shed));
        }
        if carrot_seeds == 0 && farm.money >= Crop::Carrot.seed_cost() as f64 {
            market.push(MarketOrder::BuySeed(Crop::Carrot, 1));
        }

        let mut farmer = UnitAction::Pass;
        if tile.is_empty() && carrot_seeds > 0 {
            farmer = UnitAction::Plant(Crop::Carrot);
        } else if let Tile::Plant(ref plant) = tile {
            if plant.crop == Crop::Carrot {
                let age = day - plant.planted_day;
                if age >= Crop::Carrot.max_yield_day() {
                    farmer = UnitAction::Harvest;
                } else if !plant.watered_today {
                    farmer = UnitAction::Water;
                }
            }
        }

        PlayerAction {
            farmer,
            hands: Vec::new(),
            market,
        }
    }
}

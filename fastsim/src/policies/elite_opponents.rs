//! Elite High-Elo Opponent Population Suite (1800 to 3000+ Rating Tiers).
//! Mined from authentic Kaggle ladder replays.

use super::Policy;
use super::adaptive::AdaptiveTerminalPolicy;
use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::farm::{Animal, Crop, Tile};
use crate::market::{Product, MarketOrder};

/// Tier 4A: 1800–2200 Elo — Elite Strawberry / Cow Compounder
pub struct Elite1800_2200Policy {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl Elite1800_2200Policy {
    pub fn new() -> Self {
        Self { base_adaptive: AdaptiveTerminalPolicy::new() }
    }
}

impl Policy for Elite1800_2200Policy {
    fn name(&self) -> &'static str { "elite_1800_2200" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // Day 3: Liquidate fertilizer early for liquidity
        if day == 3 && hour == 8 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 2 { action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
        }

        // Day 6: Reinvest in 4th Cow if money >= 900
        if day == 6 && hour == 16 && money >= 900.0 {
            action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
        }

        action
    }
}

/// Tier 4B: 2200–2600 Elo — Rapid Agro-Livestock Scaler
pub struct Elite2200_2600Policy {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl Elite2200_2600Policy {
    pub fn new() -> Self {
        Self { base_adaptive: AdaptiveTerminalPolicy::new() }
    }
}

impl Policy for Elite2200_2600Policy {
    fn name(&self) -> &'static str { "elite_2200_2600" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // Day 2: Buy 4 Wheat feed + 1 Worker
        if day == 2 && hour == 2 {
            if money >= 120.0 { action.market.push(MarketOrder::BuyProduct(Product::Wheat, 4)); }
            if money >= 40.0 && farm.hands.is_empty() { action.market.push(MarketOrder::Hire); }
        }

        // Day 3: Fertilizer liquidation
        if day == 3 && hour == 8 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 2 { action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
        }

        // Day 7: Quadrant 2 Land Expansion
        if day == 7 && hour == 2 && money >= 500.0 && farm.unlocked_quadrants.len() < 2 {
            action.market.push(MarketOrder::BuyLand);
        }

        action
    }
}

/// Tier 4C: 2600–3000 Elo — High-Liquidity Melon / Sheep Grandmaster
pub struct Elite2600_3000Policy {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl Elite2600_3000Policy {
    pub fn new() -> Self {
        Self { base_adaptive: AdaptiveTerminalPolicy::new() }
    }
}

impl Policy for Elite2600_3000Policy {
    fn name(&self) -> &'static str { "elite_2600_3000" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // Day 2: Buy 4 Wheat feed + 2 Workers + Melon seed
        if day == 2 && hour == 2 {
            if money >= 120.0 { action.market.push(MarketOrder::BuyProduct(Product::Wheat, 4)); }
            if money >= 80.0 && farm.hands.len() < 2 {
                action.market.push(MarketOrder::Hire);
                action.market.push(MarketOrder::Hire);
            }
            if money >= 50.0 { action.market.push(MarketOrder::BuySeed(Crop::Melon, 1)); }
        }

        // Day 3: Fertilizer liquidation
        if day == 3 && hour == 8 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 2 { action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
        }

        // Day 8: Standard 4 Sheep
        if day == 8 && hour == 4 {
            action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            if money >= 2400.0 { action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4)); }
        }

        // Day 10: Melon liquidation
        if day == 10 && hour == 20 {
            let melon = *priv_farm.shed.get("MELON").unwrap_or(&0);
            if melon > 0 { action.market.push(MarketOrder::Sell(Product::Melon, melon)); }
        }

        action
    }
}

/// Tier 4D-1: 3000+ Elo Replay 91278544 ($155,777 Peak)
pub struct Elite3000OpponentA {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl Elite3000OpponentA {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for Elite3000OpponentA {
    fn name(&self) -> &'static str { "elite_3000_opp_a_91278544" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        if day == 2 && hour == 2 {
            if money >= 120.0 { action.market.push(MarketOrder::BuyProduct(Product::Wheat, 4)); }
            if money >= 80.0 && farm.hands.len() < 2 {
                action.market.push(MarketOrder::Hire);
                action.market.push(MarketOrder::Hire);
            }
            if money >= 50.0 { action.market.push(MarketOrder::BuySeed(Crop::Melon, 1)); }
        }
        if day == 3 && hour == 8 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 2 { action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
        }
        if day == 6 && hour == 16 && money >= 900.0 {
            action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
        }
        if day == 7 && hour == 2 && money >= 500.0 && farm.unlocked_quadrants.len() < 2 {
            action.market.push(MarketOrder::BuyLand);
        }
        if day == 8 && hour == 4 {
            action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            if money >= 2400.0 { action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4)); }
            else if money >= 1200.0 { action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2)); }
            else if money >= 600.0 { action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1)); }
        }
        if day == 10 && hour == 20 {
            let melon = *priv_farm.shed.get("MELON").unwrap_or(&0);
            if melon > 0 { action.market.push(MarketOrder::Sell(Product::Melon, melon)); }
        }
        if day == 12 && hour == 2 {
            if money >= 200.0 && farm.hands.len() < 4 { action.market.push(MarketOrder::Hire); }
            let wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0);
            if money >= 500.0 && wheat < 8 { action.market.push(MarketOrder::BuyProduct(Product::Wheat, 15)); }
        }
        action
    }
}

/// Tier 4D-2: 3000+ Elo Replay 91282058 ($129,852 Peak)
pub struct Elite3000OpponentB {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl Elite3000OpponentB {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for Elite3000OpponentB {
    fn name(&self) -> &'static str { "elite_3000_opp_b_91282058" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // Day 4: Buy 1 wheat feed
        if day == 4 && hour == 4 && money >= 30.0 {
            action.market.push(MarketOrder::BuyProduct(Product::Wheat, 1));
        }
        // Day 7: Buy 4th Cow + 6 wheat feed
        if day == 7 && hour == 2 && money >= 1100.0 {
            action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
            action.market.push(MarketOrder::BuyProduct(Product::Wheat, 6));
        }
        // Day 9: Sell Fertilizer
        if day == 9 && hour == 4 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert > 0 { action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
        }
        // Day 10: Sell Melons in bulk
        if day == 10 && hour == 20 {
            let melon = *priv_farm.shed.get("MELON").unwrap_or(&0);
            if melon > 0 { action.market.push(MarketOrder::Sell(Product::Melon, melon)); }
        }
        // Day 12: Sell Wool
        if day == 12 && hour == 14 {
            let wool = *priv_farm.shed.get("WOOL").unwrap_or(&0);
            if wool > 0 { action.market.push(MarketOrder::Sell(Product::Wool, wool)); }
        }
        // Day 17: Buy feed + 1 worker
        if day == 17 && hour == 2 && money >= 200.0 {
            action.market.push(MarketOrder::BuyProduct(Product::Wheat, 4));
            action.market.push(MarketOrder::Hire);
        }
        action
    }
}

/// Tier 4D-3: 3000+ Elo Replay 91300882 ($128,990 Peak)
pub struct Elite3000OpponentC {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl Elite3000OpponentC {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for Elite3000OpponentC {
    fn name(&self) -> &'static str { "elite_3000_opp_c_91300882" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // Frequent fertilizer sell for rapid liquidity recycling
        if hour == 6 && day >= 3 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 2 { action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
        }
        // Day 6: Reinvest in cow
        if day == 6 && hour == 12 && money >= 950.0 {
            action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
        }
        // Day 8: Standard sheep
        if day == 8 && hour == 4 && money >= 2400.0 {
            action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4));
        }
        action
    }
}

/// Tier 4D-4: 3000+ Elo Replay 91304426 ($117,150 Peak)
pub struct Elite3000OpponentD {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl Elite3000OpponentD {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for Elite3000OpponentD {
    fn name(&self) -> &'static str { "elite_3000_opp_d_91304426" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let money = farm.money;

        // Defensive high-cash scaling
        if day == 6 && hour == 16 && money >= 1200.0 {
            action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
        }
        if day == 8 && hour == 4 && money >= 2400.0 {
            action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4));
        }
        if day == 11 && hour == 0 && money >= 1000.0 && farm.unlocked_quadrants.len() < 3 {
            action.market.push(MarketOrder::BuyLand);
        }
        action
    }
}


//! Adversarial Stress Opponent Suite for EXP210 Final Validation Gate.
//! Specifically stresses EXP208 against:
//! 1. Hard Mirror Opponent (Symmetric Liquidity Extraction)
//! 2. Hyper-Aggressive Agro-Livestock Scaler
//! 3. Top 3000+ Apex Compounder
//! 4. Market-Pressure Predator (Commodity Price Suppression)

use super::Policy;
use super::adaptive::AdaptiveTerminalPolicy;
use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::farm::{Animal, Crop};
use crate::market::{Product, MarketOrder};

/// 1. Hard Mirror Opponent: Symmetric Micro-Liquidity Recycling & Land Scaling
pub struct AdversarialHardMirror {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl AdversarialHardMirror {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for AdversarialHardMirror {
    fn name(&self) -> &'static str { "adv_hard_mirror" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // 3-hour continuous fertilizer micro-recycling
        if day >= 3 && hour % 3 == 0 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 2 {
                let has_sell = action.market.iter().any(|o| matches!(o, MarketOrder::Sell(Product::Fertilizer, _)));
                if !has_sell { action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
            }
        }
        // Day 2: Early wheat + 1 worker
        if day == 2 && hour == 2 {
            if money >= 120.0 { action.market.push(MarketOrder::BuyProduct(Product::Wheat, 4)); }
            if money >= 40.0 && farm.hands.is_empty() { action.market.push(MarketOrder::Hire); }
        }
        // Day 6: 4th Cow
        if day == 6 && hour == 16 && money >= 850.0 {
            action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
        }
        // Day 7: Land Q2
        if day == 7 && hour == 2 && money >= 500.0 && farm.unlocked_quadrants.len() < 2 {
            action.market.push(MarketOrder::BuyLand);
        }
        // Day 8: Sized Sheep
        if day == 8 && hour == 4 && money >= 1200.0 {
            action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
        }
        // Day 12: Land Q3
        if day == 12 && hour == 2 && money >= 810.0 && farm.unlocked_quadrants.len() < 3 {
            action.market.push(MarketOrder::BuyLand);
        }

        action
    }
}

/// 2. Hyper-Aggressive Agro-Livestock Scaler: Rapid Double-Worker & Day 5 Land Expansion
pub struct AdversarialAgroLivestock {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl AdversarialAgroLivestock {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for AdversarialAgroLivestock {
    fn name(&self) -> &'static str { "adv_agro_livestock" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // Day 2: 4 wheat feed + 2 workers
        if day == 2 && hour == 2 {
            if money >= 120.0 { action.market.push(MarketOrder::BuyProduct(Product::Wheat, 4)); }
            if money >= 80.0 && farm.hands.len() < 2 {
                action.market.push(MarketOrder::Hire);
                action.market.push(MarketOrder::Hire);
            }
        }
        // Day 3: Liquidate fertilizer
        if day == 3 && hour == 8 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 2 { action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
        }
        // Day 5: Early Land Q2
        if day == 5 && hour == 2 && money >= 500.0 && farm.unlocked_quadrants.len() < 2 {
            action.market.push(MarketOrder::BuyLand);
        }
        // Day 6: Cow 4
        if day == 6 && hour == 16 && money >= 900.0 {
            action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
        }
        // Day 8: Sheep 4
        if day == 8 && hour == 4 && money >= 2400.0 {
            action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4));
        }
        action
    }
}

/// 3. Top 3000+ Apex Compounder: Full 6-Phase Replay Compounder
pub struct AdversarialApexGrandmaster {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl AdversarialApexGrandmaster {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for AdversarialApexGrandmaster {
    fn name(&self) -> &'static str { "adv_apex_grandmaster" }

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

/// 4. Market-Pressure Predator: High-Frequency Dumper Suppressing Commodity Clearing Prices
pub struct AdversarialMarketPredator {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl AdversarialMarketPredator {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for AdversarialMarketPredator {
    fn name(&self) -> &'static str { "adv_market_predator" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let priv_farm = &state.privates[player_idx];

        // Dumps any produced goods every single hour to suppress market prices
        if day >= 2 && hour % 2 == 0 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert > 0 { action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
            let milk = *priv_farm.shed.get("MILK").unwrap_or(&0);
            if milk > 0 { action.market.push(MarketOrder::Sell(Product::Milk, milk)); }
            let wool = *priv_farm.shed.get("WOOL").unwrap_or(&0);
            if wool > 0 { action.market.push(MarketOrder::Sell(Product::Wool, wool)); }
            let straw = *priv_farm.shed.get("STRAWBERRY").unwrap_or(&0);
            if straw > 0 { action.market.push(MarketOrder::Sell(Product::Strawberry, straw)); }
        }
        action
    }
}

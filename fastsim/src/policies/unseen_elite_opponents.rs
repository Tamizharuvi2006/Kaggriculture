//! Unseen Elite Opponent Suite for EXP209 Generalization Gate.
//! Reconstructed from previously unreferenced Kaggle replay files:
//! 1. 91279421.json (Peak $115,554)
//! 2. 91283859.json (Peak $114,495)
//! 3. 91284757.json (Peak $106,545)
//! 4. 91288415.json (Peak $103,408)
//! 5. 91295596.json (Peak $102,937)

use super::Policy;
use super::adaptive::AdaptiveTerminalPolicy;
use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::farm::{Animal, Crop};
use crate::market::{Product, MarketOrder};

/// Unseen Opponent 1: Replay 91279421 ($115,554 Peak) — High-Density Wheat/Carrot Opening & Delayed Livestock
pub struct UnseenElite1800_2200 {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl UnseenElite1800_2200 {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for UnseenElite1800_2200 {
    fn name(&self) -> &'static str { "unseen_1800_2200_91279421" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // Day 2: High density carrot/wheat
        if day == 2 && hour == 2 && money >= 100.0 {
            action.market.push(MarketOrder::BuySeed(Crop::Carrot, 4));
            action.market.push(MarketOrder::BuySeed(Crop::Wheat, 4));
        }
        // Day 4: Sell early harvest
        if day == 4 && hour == 8 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 2 { action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
        }
        // Day 8: Delayed cow reinvestment
        if day == 8 && hour == 16 && money >= 1000.0 {
            action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
        }
        // Day 10: Delayed sheep transition
        if day == 10 && hour == 4 && money >= 1800.0 {
            action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
        }
        action
    }
}

/// Unseen Opponent 2: Replay 91283859 ($114,495 Peak) — Day 5 Early Land Expansion & Rapid Worker Scale
pub struct UnseenElite2200_2600 {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl UnseenElite2200_2600 {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for UnseenElite2200_2600 {
    fn name(&self) -> &'static str { "unseen_2200_2600_91283859" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let money = farm.money;

        // Day 2: 1 worker hire
        if day == 2 && hour == 2 && money >= 40.0 && farm.hands.is_empty() {
            action.market.push(MarketOrder::Hire);
        }
        // Day 5: Early Land Q2 Expansion
        if day == 5 && hour == 2 && money >= 500.0 && farm.unlocked_quadrants.len() < 2 {
            action.market.push(MarketOrder::BuyLand);
        }
        // Day 7: 2nd worker hire
        if day == 7 && hour == 2 && money >= 100.0 && farm.hands.len() < 2 {
            action.market.push(MarketOrder::Hire);
        }
        // Day 8: Sheep 2
        if day == 8 && hour == 4 && money >= 1200.0 {
            action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
        }
        action
    }
}

/// Unseen Opponent 3: Replay 91284757 ($106,545 Peak) — Milk/Wool Compounder with Day 4 Worker + Late Melon
pub struct UnseenElite2600_3000 {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl UnseenElite2600_3000 {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for UnseenElite2600_3000 {
    fn name(&self) -> &'static str { "unseen_2600_3000_91284757" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // Day 4: Hire 1 worker
        if day == 4 && hour == 0 && money >= 40.0 && farm.hands.is_empty() {
            action.market.push(MarketOrder::Hire);
        }
        // Day 6: Cow reinvestment
        if day == 6 && hour == 16 && money >= 1000.0 {
            action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
        }
        // Day 8: Buy 2 Sheep
        if day == 8 && hour == 4 && money >= 1200.0 {
            action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
        }
        // Day 14: Plant Melons
        if day == 14 && hour == 0 && money >= 200.0 {
            action.market.push(MarketOrder::BuySeed(Crop::Melon, 4));
        }
        // Day 20: Sell Melons
        if day == 20 && hour == 20 {
            let melon = *priv_farm.shed.get("MELON").unwrap_or(&0);
            if melon > 0 { action.market.push(MarketOrder::Sell(Product::Melon, melon)); }
        }
        action
    }
}

/// Unseen Opponent 4: Replay 91288415 ($103,408 Peak) — 3000+ Bot E: Hybrid Multi-Stage Scaler
pub struct UnseenElite3000_BotE {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl UnseenElite3000_BotE {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for UnseenElite3000_BotE {
    fn name(&self) -> &'static str { "unseen_3000_bote_91288415" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // Day 2: Buy 2 wheat feed + 1 worker
        if day == 2 && hour == 2 {
            if money >= 60.0 { action.market.push(MarketOrder::BuyProduct(Product::Wheat, 2)); }
            if money >= 40.0 && farm.hands.is_empty() { action.market.push(MarketOrder::Hire); }
        }
        // Day 3: Sell fertilizer
        if day == 3 && hour == 8 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 2 { action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
        }
        // Day 7: Quadrant 2
        if day == 7 && hour == 2 && money >= 500.0 && farm.unlocked_quadrants.len() < 2 {
            action.market.push(MarketOrder::BuyLand);
        }
        // Day 8: Sized Sheep
        if day == 8 && hour == 4 && money >= 1200.0 {
            action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
            action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
        }
        action
    }
}

/// Unseen Opponent 5: Replay 91295596 ($102,937 Peak) — 3000+ Bot F: Rapid Fertilizer Recycler & 3-Land Compounder
pub struct UnseenElite3000_BotF {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl UnseenElite3000_BotF {
    pub fn new() -> Self { Self { base_adaptive: AdaptiveTerminalPolicy::new() } }
}

impl Policy for UnseenElite3000_BotF {
    fn name(&self) -> &'static str { "unseen_3000_botf_91295596" }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // Continuous fertilizer sell every 6 hours
        if day >= 3 && hour % 6 == 0 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 2 { action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
        }
        // Day 6: Cow 4
        if day == 6 && hour == 16 && money >= 900.0 {
            action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
        }
        // Day 7: Land Q2
        if day == 7 && hour == 2 && money >= 500.0 && farm.unlocked_quadrants.len() < 2 {
            action.market.push(MarketOrder::BuyLand);
        }
        // Day 12: Land Q3
        if day == 12 && hour == 2 && money >= 1000.0 && farm.unlocked_quadrants.len() < 3 {
            action.market.push(MarketOrder::BuyLand);
        }
        action
    }
}

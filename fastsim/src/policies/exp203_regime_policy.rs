//! EXP203 — Regime-Conditioned Elite Action Policy + Competitive 2-Player Dynamic Lookahead Verification.
//! Identifies economic regimes (Fast-Growth, Low-Liquidity, Market-Crash, Standard-Safe),
//! proposes surgical elite macro transitions, and verifies competitive margin delta in 2-player simulation.

use super::Policy;
use super::adaptive::AdaptiveTerminalPolicy;
use crate::engine::state::GameState;
use crate::engine::step::{step_game, PlayerAction};
use crate::farm::{Animal, Crop, Tile};
use crate::market::{Product, MarketOrder};

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum MacroCandidate {
    None,
    EarlyFastGrowthDay2,     // Day 2: Buy 4 Wheat Product + Hire 1 Worker + Buy 1 Melon Seed
    FertilizerDumpDay3,      // Day 3: Instant Fertilizer Liquidation
    FourthCowReinvestDay6,   // Day 6: Buy 4th Cow
    LandExpansionQ2Day7,     // Day 7: Buy Land Q2
    MelonLiquidationDay10,   // Day 10: Sell Melons
    SheepSized1Day8,         // Day 8: Buy 1 Sheep
    SheepSized2Day8,         // Day 8: Buy 2 Sheep
    SheepStandard4Day8,      // Day 8: Buy 4 Sheep
}

pub struct EXP203RegimePolicy {
    base_adaptive: AdaptiveTerminalPolicy,
}

impl EXP203RegimePolicy {
    pub fn new() -> Self {
        Self {
            base_adaptive: AdaptiveTerminalPolicy::new(),
        }
    }

    /// Macro Regime Classifier
    pub fn classify_regime(state: &GameState, player_idx: usize) -> (bool, bool, bool) {
        let p_fert = *state.market.prices.get(&Product::Fertilizer).unwrap_or(&80) as f64;
        let p_wheat = *state.market.prices.get(&Product::Wheat).unwrap_or(&30) as f64;
        let p_milk = *state.market.prices.get(&Product::Milk).unwrap_or(&160) as f64;
        let p_wool = *state.market.prices.get(&Product::Wool).unwrap_or(&180) as f64;
        let cash = state.farms[player_idx].money;

        let is_fast_growth = p_fert >= 65.0 && p_wheat <= 40.0 && p_milk >= 130.0;
        let is_low_liquidity = cash < 800.0 && state.day >= 6;
        let is_market_crash = p_milk < 110.0 || p_wool < 130.0;

        (is_fast_growth, is_low_liquidity, is_market_crash)
    }

    /// 2-Player Dynamic Lookahead Competitive Margin Verifier:
    /// Simulates BOTH Hero and Opponent executing dynamic adaptive policies to step 720
    pub fn verify_candidate_margin(
        state: &GameState,
        player_idx: usize,
        candidate: MacroCandidate,
        base_act: &PlayerAction,
    ) -> (f64, bool) {
        let opp_policy = AdaptiveTerminalPolicy::new();
        let eval_hero = AdaptiveTerminalPolicy::new();
        let eval_opp = AdaptiveTerminalPolicy::new();

        // 1. Baseline 2-player rollout (a0)
        let mut base_st = state.clone();
        let opp_act_0 = opp_policy.act(&base_st, 1 - player_idx);

        let actions_base = if player_idx == 0 {
            [base_act.clone(), opp_act_0.clone()]
        } else {
            [opp_act_0.clone(), base_act.clone()]
        };
        step_game(&mut base_st, &[actions_base[0].clone(), actions_base[1].clone()]);

        while !base_st.done {
            let a0 = eval_hero.act(&base_st, 0);
            let a1 = eval_opp.act(&base_st, 1);
            step_game(&mut base_st, &[a0, a1]);
        }
        let base_hero = base_st.farms[player_idx].money;
        let base_opp = base_st.farms[1 - player_idx].money;
        let base_margin = base_hero - base_opp;

        // 2. Candidate 2-player rollout
        let mut cf_st = state.clone();
        let mut cand_hero_act = base_act.clone();

        match candidate {
            MacroCandidate::EarlyFastGrowthDay2 => {
                if cf_st.farms[player_idx].money >= 120.0 {
                    cand_hero_act.market.push(MarketOrder::BuyProduct(Product::Wheat, 4));
                }
                if cf_st.farms[player_idx].money >= 40.0 && cf_st.farms[player_idx].hands.is_empty() {
                    cand_hero_act.market.push(MarketOrder::Hire);
                }
                if cf_st.farms[player_idx].money >= 50.0 {
                    cand_hero_act.market.push(MarketOrder::BuySeed(Crop::Melon, 1));
                }
            }
            MacroCandidate::FertilizerDumpDay3 => {
                let fert = *cf_st.privates[player_idx].shed.get("FERTILIZER").unwrap_or(&0);
                if fert >= 2 {
                    cand_hero_act.market.push(MarketOrder::Sell(Product::Fertilizer, fert));
                }
            }
            MacroCandidate::FourthCowReinvestDay6 => {
                if cf_st.farms[player_idx].money >= 1000.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
                }
            }
            MacroCandidate::LandExpansionQ2Day7 => {
                if cf_st.farms[player_idx].money >= 500.0 && cf_st.farms[player_idx].unlocked_quadrants.len() < 2 {
                    cand_hero_act.market.push(MarketOrder::BuyLand);
                }
            }
            MacroCandidate::MelonLiquidationDay10 => {
                let melon = *cf_st.privates[player_idx].shed.get("MELON").unwrap_or(&0);
                if melon > 0 {
                    cand_hero_act.market.push(MarketOrder::Sell(Product::Melon, melon));
                }
            }
            MacroCandidate::SheepSized1Day8 => {
                cand_hero_act.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                if cf_st.farms[player_idx].money >= 600.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1));
                }
            }
            MacroCandidate::SheepSized2Day8 => {
                cand_hero_act.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                if cf_st.farms[player_idx].money >= 1200.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
                }
            }
            MacroCandidate::SheepStandard4Day8 => {
                cand_hero_act.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                if cf_st.farms[player_idx].money >= 2400.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4));
                }
            }
            MacroCandidate::None => {}
        }

        let actions_cf = if player_idx == 0 {
            [cand_hero_act, opp_act_0]
        } else {
            [opp_act_0, cand_hero_act]
        };
        step_game(&mut cf_st, &[actions_cf[0].clone(), actions_cf[1].clone()]);

        while !cf_st.done {
            let a0 = eval_hero.act(&cf_st, 0);
            let a1 = eval_opp.act(&cf_st, 1);
            step_game(&mut cf_st, &[a0, a1]);
        }
        let cf_hero = cf_st.farms[player_idx].money;
        let cf_opp = cf_st.farms[1 - player_idx].money;
        let cf_margin = cf_hero - cf_opp;

        let delta_margin = cf_margin - base_margin;
        let safe_to_execute = cf_hero >= cf_opp || delta_margin >= 300.0;

        (delta_margin, safe_to_execute)
    }
}

impl Policy for EXP203RegimePolicy {
    fn name(&self) -> &'static str {
        "exp203_regime_policy"
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        let (is_fast_growth, is_low_liquidity, is_market_crash) = Self::classify_regime(state, player_idx);

        // Sparse Scheduled Regime-Conditioned Checkpoints:
        let candidate: MacroCandidate = if day == 2 && hour == 2 {
            if is_fast_growth && money >= 200.0 {
                MacroCandidate::EarlyFastGrowthDay2
            } else {
                MacroCandidate::None
            }
        } else if day == 3 && hour == 8 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 2 {
                MacroCandidate::FertilizerDumpDay3
            } else {
                MacroCandidate::None
            }
        } else if day == 6 && hour == 16 {
            if is_fast_growth && money >= 1000.0 {
                MacroCandidate::FourthCowReinvestDay6
            } else {
                MacroCandidate::None
            }
        } else if day == 7 && hour == 2 {
            if is_fast_growth && money >= 500.0 && farm.unlocked_quadrants.len() < 2 {
                MacroCandidate::LandExpansionQ2Day7
            } else {
                MacroCandidate::None
            }
        } else if day == 8 && hour == 4 {
            if is_low_liquidity || is_market_crash {
                if money >= 1200.0 {
                    MacroCandidate::SheepSized2Day8
                } else if money >= 600.0 {
                    MacroCandidate::SheepSized1Day8
                } else {
                    MacroCandidate::None
                }
            } else if is_fast_growth && money >= 2400.0 {
                MacroCandidate::SheepStandard4Day8
            } else {
                MacroCandidate::None
            }
        } else if day == 10 && hour == 20 {
            let melon = *priv_farm.shed.get("MELON").unwrap_or(&0);
            if melon > 0 {
                MacroCandidate::MelonLiquidationDay10
            } else {
                MacroCandidate::None
            }
        } else {
            MacroCandidate::None
        };

        if candidate != MacroCandidate::None {
            // Run 2-Player Dynamic Lookahead Margin Verification
            let (delta_margin, safe_to_execute) = Self::verify_candidate_margin(state, player_idx, candidate, &base_action);

            if delta_margin >= 150.0 && safe_to_execute {
                match candidate {
                    MacroCandidate::EarlyFastGrowthDay2 => {
                        if money >= 120.0 {
                            base_action.market.push(MarketOrder::BuyProduct(Product::Wheat, 4));
                        }
                        if money >= 40.0 && farm.hands.is_empty() {
                            base_action.market.push(MarketOrder::Hire);
                        }
                        if money >= 50.0 {
                            base_action.market.push(MarketOrder::BuySeed(Crop::Melon, 1));
                        }
                    }
                    MacroCandidate::FertilizerDumpDay3 => {
                        let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
                        if fert >= 2 {
                            base_action.market.push(MarketOrder::Sell(Product::Fertilizer, fert));
                        }
                    }
                    MacroCandidate::FourthCowReinvestDay6 => {
                        if money >= 1000.0 {
                            base_action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
                        }
                    }
                    MacroCandidate::LandExpansionQ2Day7 => {
                        if money >= 500.0 && farm.unlocked_quadrants.len() < 2 {
                            base_action.market.push(MarketOrder::BuyLand);
                        }
                    }
                    MacroCandidate::MelonLiquidationDay10 => {
                        let melon = *priv_farm.shed.get("MELON").unwrap_or(&0);
                        if melon > 0 {
                            base_action.market.push(MarketOrder::Sell(Product::Melon, melon));
                        }
                    }
                    MacroCandidate::SheepSized1Day8 => {
                        base_action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                        if money >= 600.0 {
                            base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1));
                        }
                    }
                    MacroCandidate::SheepSized2Day8 => {
                        base_action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                        if money >= 1200.0 {
                            base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
                        }
                    }
                    MacroCandidate::SheepStandard4Day8 => {
                        base_action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                        if money >= 2400.0 {
                            base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4));
                        }
                    }
                    MacroCandidate::None => {}
                }
            }
        }

        base_action
    }
}

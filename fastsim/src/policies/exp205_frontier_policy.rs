//! EXP205 — Elite Frontier Candidate #1 Policy (Mined via GPU 100M-Evaluation Search).
//! Configuration: FertMin=$53.0, CowThresh=$819.0, SheepFast=4, MarginGate=$201.0.

use super::Policy;
use super::adaptive::AdaptiveTerminalPolicy;
use crate::engine::state::GameState;
use crate::engine::step::{step_game, PlayerAction};
use crate::farm::{Animal, Crop, Tile};
use crate::market::{Product, MarketOrder};

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum FrontierCandidate {
    None,
    EarlyWheatFeedDay2,
    EarlyWorkerDay2,
    EarlyMelonDay2,
    FertilizerDumpDay3,
    FourthCowDay6,
    Quadrant2Day7,
    SheepExpansionDay8,
    MelonLiquidationDay10,
}

pub struct EXP205FrontierPolicy {
    base_adaptive: AdaptiveTerminalPolicy,
    fert_sell_min: f64,
    cow_reinvest_thresh: f64,
    sheep_fast_size: i64,
    margin_gate: f64,
}

impl EXP205FrontierPolicy {
    pub fn new() -> Self {
        Self {
            base_adaptive: AdaptiveTerminalPolicy::new(),
            fert_sell_min: 53.0,
            cow_reinvest_thresh: 819.0,
            sheep_fast_size: 4,
            margin_gate: 201.0,
        }
    }

    /// 2-Player Dynamic Lookahead Margin Verifier
    pub fn verify_candidate_margin(
        &self,
        state: &GameState,
        player_idx: usize,
        candidate: FrontierCandidate,
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
        let money = cf_st.farms[player_idx].money;

        match candidate {
            FrontierCandidate::EarlyWheatFeedDay2 => {
                if money >= 120.0 { cand_hero_act.market.push(MarketOrder::BuyProduct(Product::Wheat, 4)); }
            }
            FrontierCandidate::EarlyWorkerDay2 => {
                if money >= 40.0 { cand_hero_act.market.push(MarketOrder::Hire); }
            }
            FrontierCandidate::EarlyMelonDay2 => {
                if money >= 50.0 { cand_hero_act.market.push(MarketOrder::BuySeed(Crop::Melon, 1)); }
            }
            FrontierCandidate::FertilizerDumpDay3 => {
                let fert = *cf_st.privates[player_idx].shed.get("FERTILIZER").unwrap_or(&0);
                if fert >= 2 { cand_hero_act.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
            }
            FrontierCandidate::FourthCowDay6 => {
                if money >= self.cow_reinvest_thresh { cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1)); }
            }
            FrontierCandidate::Quadrant2Day7 => {
                if money >= 500.0 && cf_st.farms[player_idx].unlocked_quadrants.len() < 2 {
                    cand_hero_act.market.push(MarketOrder::BuyLand);
                }
            }
            FrontierCandidate::SheepExpansionDay8 => {
                cand_hero_act.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                if money >= 2400.0 && self.sheep_fast_size == 4 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4));
                } else if money >= 1200.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
                } else if money >= 600.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1));
                }
            }
            FrontierCandidate::MelonLiquidationDay10 => {
                let melon = *cf_st.privates[player_idx].shed.get("MELON").unwrap_or(&0);
                if melon > 0 { cand_hero_act.market.push(MarketOrder::Sell(Product::Melon, melon)); }
            }
            FrontierCandidate::None => {}
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

impl Policy for EXP205FrontierPolicy {
    fn name(&self) -> &'static str {
        "exp205_frontier_policy"
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        let p_fert = *state.market.prices.get(&Product::Fertilizer).unwrap_or(&80) as f64;
        let p_wheat = *state.market.prices.get(&Product::Wheat).unwrap_or(&30) as f64;
        let p_milk = *state.market.prices.get(&Product::Milk).unwrap_or(&160) as f64;

        let cand: FrontierCandidate = if day == 2 && hour == 2 {
            if p_fert >= self.fert_sell_min && p_wheat <= 38.0 && money >= 150.0 {
                FrontierCandidate::EarlyWheatFeedDay2
            } else {
                FrontierCandidate::None
            }
        } else if day == 3 && hour == 8 {
            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
            if fert >= 2 && p_fert >= self.fert_sell_min {
                FrontierCandidate::FertilizerDumpDay3
            } else {
                FrontierCandidate::None
            }
        } else if day == 6 && hour == 16 {
            if money >= self.cow_reinvest_thresh && p_milk >= 130.0 {
                FrontierCandidate::FourthCowDay6
            } else {
                FrontierCandidate::None
            }
        } else if day == 7 && hour == 2 {
            if money >= 500.0 && farm.unlocked_quadrants.len() < 2 {
                FrontierCandidate::Quadrant2Day7
            } else {
                FrontierCandidate::None
            }
        } else if day == 8 && hour == 4 {
            if money >= 600.0 {
                FrontierCandidate::SheepExpansionDay8
            } else {
                FrontierCandidate::None
            }
        } else if day == 10 && hour == 20 {
            let melon = *priv_farm.shed.get("MELON").unwrap_or(&0);
            if melon > 0 {
                FrontierCandidate::MelonLiquidationDay10
            } else {
                FrontierCandidate::None
            }
        } else {
            FrontierCandidate::None
        };

        if cand != FrontierCandidate::None {
            let (delta_margin, safe_to_execute) = self.verify_candidate_margin(state, player_idx, cand, &base_action);

            if delta_margin >= self.margin_gate && safe_to_execute {
                match cand {
                    FrontierCandidate::EarlyWheatFeedDay2 => {
                        if money >= 120.0 { base_action.market.push(MarketOrder::BuyProduct(Product::Wheat, 4)); }
                        if money >= 40.0 && farm.hands.is_empty() { base_action.market.push(MarketOrder::Hire); }
                        if money >= 50.0 { base_action.market.push(MarketOrder::BuySeed(Crop::Melon, 1)); }
                    }
                    FrontierCandidate::FertilizerDumpDay3 => {
                        let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
                        if fert >= 2 { base_action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
                    }
                    FrontierCandidate::FourthCowDay6 => {
                        if money >= self.cow_reinvest_thresh { base_action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1)); }
                    }
                    FrontierCandidate::Quadrant2Day7 => {
                        if money >= 500.0 && farm.unlocked_quadrants.len() < 2 { base_action.market.push(MarketOrder::BuyLand); }
                    }
                    FrontierCandidate::SheepExpansionDay8 => {
                        base_action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                        if money >= 2400.0 && self.sheep_fast_size == 4 { base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4)); }
                        else if money >= 1200.0 { base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2)); }
                        else if money >= 600.0 { base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1)); }
                    }
                    FrontierCandidate::MelonLiquidationDay10 => {
                        let melon = *priv_farm.shed.get("MELON").unwrap_or(&0);
                        if melon > 0 { base_action.market.push(MarketOrder::Sell(Product::Melon, melon)); }
                    }
                    FrontierCandidate::None => {}
                    _ => {}
                }
            }
        }

        base_action
    }
}

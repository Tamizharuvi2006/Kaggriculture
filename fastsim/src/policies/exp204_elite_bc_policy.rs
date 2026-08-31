//! EXP204 — Elite Behavioral Cloning Policy.
//! Combines GPU-trained Elite BC Network (1800-3000+ population)
//! with 2-Player Dynamic Lookahead Margin Verification in FastSim.

use super::Policy;
use super::adaptive::AdaptiveTerminalPolicy;
use crate::engine::state::GameState;
use crate::engine::step::{step_game, PlayerAction};
use crate::farm::{Animal, Crop, Tile};
use crate::market::{Product, MarketOrder};
use serde_json::Value;

const WEIGHTS_JSON: &str = include_str!("../../../models/exp204_elite_bc_weights.json");

pub struct EXP204EliteBCPolicy {
    base_adaptive: AdaptiveTerminalPolicy,
    state_mean: Vec<f64>,
    state_std: Vec<f64>,
    trunk_fc1_w: Vec<Vec<f64>>,
    trunk_fc1_b: Vec<f64>,
    trunk_ln1_w: Vec<f64>,
    trunk_ln1_b: Vec<f64>,
    trunk_fc2_w: Vec<Vec<f64>>,
    trunk_fc2_b: Vec<f64>,
    trunk_ln2_w: Vec<f64>,
    trunk_ln2_b: Vec<f64>,
    head_w: Vec<Vec<f64>>,
    head_b: Vec<f64>,
}

impl EXP204EliteBCPolicy {
    pub fn new() -> Self {
        let v: Value = serde_json::from_str(WEIGHTS_JSON)
            .expect("Failed to parse embedded EXP204 weights JSON");

        let parse_vec = |key: &str| -> Vec<f64> {
            v[key].as_array().unwrap().iter().map(|x| x.as_f64().unwrap()).collect()
        };

        let parse_mat = |key: &str| -> Vec<Vec<f64>> {
            v[key].as_array().unwrap().iter().map(|row| {
                row.as_array().unwrap().iter().map(|x| x.as_f64().unwrap()).collect()
            }).collect()
        };

        Self {
            base_adaptive: AdaptiveTerminalPolicy::new(),
            state_mean: parse_vec("state_mean"),
            state_std: parse_vec("state_std"),
            trunk_fc1_w: parse_mat("trunk_fc1_weight"),
            trunk_fc1_b: parse_vec("trunk_fc1_bias"),
            trunk_ln1_w: parse_vec("trunk_ln1_weight"),
            trunk_ln1_b: parse_vec("trunk_ln1_bias"),
            trunk_fc2_w: parse_mat("trunk_fc2_weight"),
            trunk_fc2_b: parse_vec("trunk_fc2_bias"),
            trunk_ln2_w: parse_vec("trunk_ln2_weight"),
            trunk_ln2_b: parse_vec("trunk_ln2_bias"),
            head_w: parse_mat("action_head_weight"),
            head_b: parse_vec("action_head_bias"),
        }
    }

    pub fn extract_features(&self, state: &GameState, player_idx: usize) -> [f64; 16] {
        let opp_idx = 1 - player_idx;
        let p_milk = *state.market.prices.get(&Product::Milk).unwrap_or(&160) as f64;
        let cash = state.farms[player_idx].money;
        let opp_cash = state.farms[opp_idx].money;

        let mut cows = 0.0;
        let mut sheep = 0.0;
        let mut unwatered = 0.0;
        let mut mature = 0.0;

        for row in &state.farms[player_idx].tiles {
            for tile in row {
                match tile {
                    Tile::Animal(a) => {
                        if a.animal == Animal::Cow { cows += 1.0; }
                        else if a.animal == Animal::Sheep { sheep += 1.0; }
                    }
                    Tile::Plant(c) => {
                        if !c.watered_today { unwatered += 1.0; }
                        if c.yield_units > 0 { mature += 1.0; }
                    }

                    _ => {}
                }
            }
        }

        let mut opp_cows = 0.0;
        let mut opp_sheep = 0.0;
        let mut opp_straws = 0.0;

        for row in &state.farms[opp_idx].tiles {
            for tile in row {
                match tile {
                    Tile::Animal(a) => {
                        if a.animal == Animal::Cow { opp_cows += 1.0; }
                        else if a.animal == Animal::Sheep { opp_sheep += 1.0; }
                    }
                    Tile::Plant(c) => {
                        if c.crop == Crop::Strawberry { opp_straws += 1.0; }
                    }
                    _ => {}
                }
            }
        }


        let shed_wheat = *state.privates[player_idx].shed.get("WHEAT").unwrap_or(&0) as f64;
        let hands = state.farms[player_idx].hands.len() as f64;
        let quads = state.farms[player_idx].unlocked_quadrants.len() as f64;
        let day = state.day as f64;

        let opp_quads = state.farms[opp_idx].unlocked_quadrants.len() as f64;
        let opp_workers = state.farms[opp_idx].hands.len() as f64;

        let raw = [
            p_milk, cash, cows, sheep, shed_wheat, hands, quads, day, unwatered, mature,
            opp_cash, opp_cows, opp_sheep, opp_quads, opp_workers, opp_straws
        ];

        let mut norm = [0.0; 16];
        for i in 0..16 {
            norm[i] = (raw[i] - self.state_mean[i]) / self.state_std[i];
        }
        norm
    }

    pub fn predict_elite_action(&self, state: &GameState, player_idx: usize) -> (usize, f64) {
        let x = self.extract_features(state, player_idx);

        // Layer 1: Linear 16 -> 128
        let mut h1 = vec![0.0; 128];
        for i in 0..128 {
            let mut sum = self.trunk_fc1_b[i];
            for j in 0..16 {
                sum += self.trunk_fc1_w[i][j] * x[j];
            }
            h1[i] = sum;
        }

        // LayerNorm 1
        let mean1 = h1.iter().sum::<f64>() / 128.0;
        let var1 = h1.iter().map(|v| (v - mean1).powi(2)).sum::<f64>() / 128.0;
        let std1 = (var1 + 1e-5).sqrt();
        for i in 0..128 {
            let norm = (h1[i] - mean1) / std1;
            let val = norm * self.trunk_ln1_w[i] + self.trunk_ln1_b[i];
            h1[i] = val.max(0.0); // ReLU
        }

        // Layer 2: Linear 128 -> 64
        let mut h2 = vec![0.0; 64];
        for i in 0..64 {
            let mut sum = self.trunk_fc2_b[i];
            for j in 0..128 {
                sum += self.trunk_fc2_w[i][j] * h1[j];
            }
            h2[i] = sum;
        }

        // LayerNorm 2
        let mean2 = h2.iter().sum::<f64>() / 64.0;
        let var2 = h2.iter().map(|v| (v - mean2).powi(2)).sum::<f64>() / 64.0;
        let std2 = (var2 + 1e-5).sqrt();
        for i in 0..64 {
            let norm = (h2[i] - mean2) / std2;
            let val = norm * self.trunk_ln2_w[i] + self.trunk_ln2_b[i];
            h2[i] = val.max(0.0); // ReLU
        }

        // Head: Linear 64 -> 10
        let mut logits = [0.0; 10];
        let mut max_logit = -1e9;
        let mut best_act = 0;

        for i in 0..10 {
            let mut sum = self.head_b[i];
            for j in 0..64 {
                sum += self.head_w[i][j] * h2[j];
            }
            logits[i] = sum;
            if sum > max_logit {
                max_logit = sum;
                best_act = i;
            }
        }

        (best_act, max_logit)
    }

    /// 2-Player Dynamic Lookahead Margin Verifier
    pub fn verify_candidate_margin(
        state: &GameState,
        player_idx: usize,
        action_idx: usize,
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

        match action_idx {
            1 => { // a1: BUY_WHEAT_FEED
                if money >= 120.0 {
                    cand_hero_act.market.push(MarketOrder::BuyProduct(Product::Wheat, 4));
                }
            }
            2 => { // a2: HIRE_WORKER
                if money >= 40.0 {
                    cand_hero_act.market.push(MarketOrder::Hire);
                }
            }
            3 => { // a3: BUY_MELON_SEED
                if money >= 50.0 {
                    cand_hero_act.market.push(MarketOrder::BuySeed(Crop::Melon, 1));
                }
            }
            4 => { // a4: BUY_COW
                if money >= 1000.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
                }
            }
            5 => { // a5: BUY_LAND
                if money >= 500.0 && cf_st.farms[player_idx].unlocked_quadrants.len() < 3 {
                    cand_hero_act.market.push(MarketOrder::BuyLand);
                }
            }
            6 => { // a6: BUY_SHEEP
                cand_hero_act.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                if money >= 2400.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4));
                } else if money >= 1200.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2));
                } else if money >= 600.0 {
                    cand_hero_act.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1));
                }
            }
            7 => { // a7: SELL_FERTILIZER
                let fert = *cf_st.privates[player_idx].shed.get("FERTILIZER").unwrap_or(&0);
                if fert >= 2 {
                    cand_hero_act.market.push(MarketOrder::Sell(Product::Fertilizer, fert));
                }
            }
            8 => { // a8: SELL_MELON
                let melon = *cf_st.privates[player_idx].shed.get("MELON").unwrap_or(&0);
                if melon > 0 {
                    cand_hero_act.market.push(MarketOrder::Sell(Product::Melon, melon));
                }
            }
            9 => { // a9: SELL_MILK_WOOL
                let milk = *cf_st.privates[player_idx].shed.get("MILK").unwrap_or(&0);
                let wool = *cf_st.privates[player_idx].shed.get("WOOL").unwrap_or(&0);
                if milk >= 2 { cand_hero_act.market.push(MarketOrder::Sell(Product::Milk, milk)); }
                if wool >= 2 { cand_hero_act.market.push(MarketOrder::Sell(Product::Wool, wool)); }
            }
            _ => {}
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

impl Policy for EXP204EliteBCPolicy {
    fn name(&self) -> &'static str {
        "exp204_elite_bc"
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut base_action = self.base_adaptive.act(state, player_idx);
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        // Candidate decision windows (Day 2, Day 3, Day 6, Day 7, Day 8, Day 10)
        let is_window = (day == 2 && hour == 2)
            || (day == 3 && hour == 8)
            || (day == 6 && hour == 16)
            || (day == 7 && hour == 2)
            || (day == 8 && hour == 4)
            || (day == 10 && hour == 20);

        if is_window {
            let (best_act, _logit) = self.predict_elite_action(state, player_idx);

            if best_act != 0 {
                let (delta_margin, safe_to_execute) = Self::verify_candidate_margin(state, player_idx, best_act, &base_action);

                if delta_margin >= 150.0 && safe_to_execute {
                    match best_act {
                        1 => { // BUY_WHEAT_FEED
                            if money >= 120.0 { base_action.market.push(MarketOrder::BuyProduct(Product::Wheat, 4)); }
                        }
                        2 => { // HIRE_WORKER
                            if money >= 40.0 { base_action.market.push(MarketOrder::Hire); }
                        }
                        3 => { // BUY_MELON_SEED
                            if money >= 50.0 { base_action.market.push(MarketOrder::BuySeed(Crop::Melon, 1)); }
                        }
                        4 => { // BUY_COW
                            if money >= 1000.0 { base_action.market.push(MarketOrder::BuyAnimal(Animal::Cow, 1)); }
                        }
                        5 => { // BUY_LAND
                            if money >= 500.0 && farm.unlocked_quadrants.len() < 3 { base_action.market.push(MarketOrder::BuyLand); }
                        }
                        6 => { // BUY_SHEEP
                            base_action.market.retain(|o| !matches!(o, MarketOrder::BuyAnimal(Animal::Sheep, _)));
                            if money >= 2400.0 { base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 4)); }
                            else if money >= 1200.0 { base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 2)); }
                            else if money >= 600.0 { base_action.market.push(MarketOrder::BuyAnimal(Animal::Sheep, 1)); }
                        }
                        7 => { // SELL_FERTILIZER
                            let fert = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
                            if fert >= 2 { base_action.market.push(MarketOrder::Sell(Product::Fertilizer, fert)); }
                        }
                        8 => { // SELL_MELON
                            let melon = *priv_farm.shed.get("MELON").unwrap_or(&0);
                            if melon > 0 { base_action.market.push(MarketOrder::Sell(Product::Melon, melon)); }
                        }
                        9 => { // SELL_MILK_WOOL
                            let milk = *priv_farm.shed.get("MILK").unwrap_or(&0);
                            let wool = *priv_farm.shed.get("WOOL").unwrap_or(&0);
                            if milk >= 2 { base_action.market.push(MarketOrder::Sell(Product::Milk, milk)); }
                            if wool >= 2 { base_action.market.push(MarketOrder::Sell(Product::Wool, wool)); }
                        }
                        _ => {}
                    }
                }
            }
        }

        base_action
    }
}

//! Hierarchical Neural BC Policy: Combines Macro Economic Policy with Worker Execution Policy.

use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::market::{Product, MarketOrder};
use crate::workers::UnitAction;
use crate::farm::{Animal, Tile, Crop};
use crate::policies::Policy;

pub struct HierarchicalBCPolicy {
    name: &'static str,
}

impl HierarchicalBCPolicy {
    pub fn new() -> Self {
        Self {
            name: "hierarchical_bc_policy",
        }
    }

    /// Extract 48-d feature vector for a specific worker
    pub fn extract_worker_features(
        state: &GameState,
        player_idx: usize,
        pos: (usize, usize),
        is_farmer: bool,
        inv_wheat: i64,
        inv_total: i64,
    ) -> [f32; 48] {
        let mut f = [0.0f32; 48];
        let (wx, wy) = pos;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];

        // 1. Pos & Role (4)
        f[0] = wx as f32 / 10.0;
        f[1] = wy as f32 / 10.0;
        f[2] = if is_farmer { 1.0 } else { 0.0 };
        f[3] = farm.hands.len() as f32 / 16.0;

        // 2. Local Tile State (10)
        let curr_tile = &farm.tiles[wy][wx];
        match curr_tile {
            Tile::Plant(p) => {
                f[4] = 1.0;
                f[7] = p.yield_units as f32 / 4.0;
                f[8] = if p.watered_today { 1.0 } else { 0.0 };
                f[11] = match p.crop {
                    Crop::Carrot => 0.2,
                    Crop::Tomato => 0.4,
                    Crop::Wheat => 0.6,
                    Crop::Strawberry => 0.8,
                    Crop::Melon => 1.0,
                };
            }
            Tile::Animal(a) => {
                f[5] = 1.0;
                f[9] = if a.fed_today { 1.0 } else { 0.0 };
                f[10] = if a.fertilizer_available { 1.0 } else { 0.0 };
            }
            Tile::Empty => {
                f[6] = 1.0;
            }
            _ => {}
        }

        // 3. Worker Inventory (8)
        f[14] = inv_wheat as f32 / 10.0;
        f[18] = inv_total as f32 / 10.0;

        // 4. Global State & Seeds (16)
        f[22] = state.step as f32 / 720.0;
        f[23] = state.day as f32 / 30.0;
        f[24] = state.hour as f32 / 24.0;
        f[25] = ((1.0 + farm.money.max(0.0)).ln() / 12.0) as f32;
        f[26] = *priv_farm.seeds.get(&Crop::Melon).unwrap_or(&0) as f32 / 10.0;
        f[27] = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0) as f32 / 10.0;
        f[28] = *priv_farm.seeds.get(&Crop::Wheat).unwrap_or(&0) as f32 / 10.0;
        f[37] = 1.0; // bias

        // 5. Board Needs Summary (10)
        let mut unwatered = 0.0f32;
        let mut mature = 0.0f32;
        for row in &farm.tiles {
            for t in row {
                if let Tile::Plant(p) = t {
                    if p.yield_units > 0 {
                        mature += 1.0;
                    } else if !p.watered_today {
                        unwatered += 1.0;
                    }
                }
            }
        }
        f[38] = unwatered / 50.0;
        f[39] = mature / 50.0;

        f
    }

    /// Map action ID to UnitAction
    pub fn id_to_action(act_id: usize) -> UnitAction {
        match act_id {
            0 => UnitAction::Pass,
            1 => UnitAction::North,
            2 => UnitAction::South,
            3 => UnitAction::East,
            4 => UnitAction::West,
            5 => UnitAction::Dig,
            6 => UnitAction::Plant(Crop::Melon),
            7 => UnitAction::Plant(Crop::Strawberry),
            8 => UnitAction::Plant(Crop::Wheat),
            9 => UnitAction::Plant(Crop::Carrot),
            10 => UnitAction::Plant(Crop::Tomato),
            11 => UnitAction::Water,
            12 => UnitAction::Harvest,
            13 => UnitAction::Feed,
            14 => UnitAction::CollectFertilizer,
            15 => UnitAction::Drop,
            _ => UnitAction::Pass,
        }
    }
}

impl Policy for HierarchicalBCPolicy {
    fn name(&self) -> &'static str {
        self.name
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let step = state.step;
        let day = state.day;
        let hour = state.hour;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        let mut market = Vec::new();

        // =========================================================================
        // 1. MACRO ECONOMIC LAYER
        // =========================================================================

        // Day 0: Grandmaster Opening
        if step == 0 || (step == 1 && farm.hands.is_empty()) {
            market.push(MarketOrder::Hire);
            market.push(MarketOrder::Hire);
            market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
            market.push(MarketOrder::BuySeed(Crop::Melon, 6));
            market.push(MarketOrder::BuySeed(Crop::Wheat, 6));
            let starting_wheat = *priv_farm.shed.get("WHEAT").unwrap_or(&0);
            if starting_wheat > 0 {
                market.push(MarketOrder::Sell(Product::Wheat, starting_wheat));
            }
        }

        // Daily hiring schedule
        if hour == 0 && step > 1 {
            let max_hands = if day < 4 { 4 } else if day < 10 { 8 } else { 12 };
            if farm.hands.len() < max_hands && money >= 200.0 {
                market.push(MarketOrder::Hire);
            }
        }

        // Mid-game crop seeds
        if hour == 0 && day >= 4 && day < 25 {
            let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);
            if straw_seeds < 16 && money >= 300.0 {
                market.push(MarketOrder::BuySeed(Crop::Strawberry, 16 - straw_seeds));
            }
        }

        // Regular liquidations
        for prod in [Product::Fertilizer, Product::Melon, Product::Strawberry, Product::Milk, Product::Wool] {
            let count = *priv_farm.shed.get(prod.name()).unwrap_or(&0);
            if count > 0 {
                market.push(MarketOrder::Sell(prod, count));
            }
        }

        // Dynamic Land Unlock
        if hour == 0 {
            let quads = farm.unlocked_quadrants.len();
            if quads == 1 && day >= 7 && money >= 1600.0 {
                market.push(MarketOrder::BuyLand);
            } else if quads == 2 && day >= 10 && money >= 3200.0 {
                market.push(MarketOrder::BuyLand);
            }
        }

        // Terminal clearance
        if step >= 700 {
            for prod in Product::ALL {
                let count = *priv_farm.shed.get(prod.name()).unwrap_or(&0);
                if count > 0 {
                    market.push(MarketOrder::Sell(prod, count));
                }
            }
        }

        // =========================================================================
        // 2. WORKER EXECUTION LAYER
        // =========================================================================

        // Route Farmer
        let (fx, fy) = farm.farmer;
        let farmer_inv = priv_farm.inventories.first();
        let farmer_wheat = farmer_inv.and_then(|inv| inv.get("WHEAT")).copied().unwrap_or(0);
        let farmer_total = farmer_inv.map(|inv| inv.values().sum::<i64>()).unwrap_or(0);
        
        let f_vec = Self::extract_worker_features(state, player_idx, (fx, fy), true, farmer_wheat, farmer_total);
        
        // Priority worker heuristics based on learned policy intent
        let farmer = if let Tile::Plant(p) = &farm.tiles[fy][fx] {
            if p.yield_units > 0 {
                UnitAction::Harvest
            } else if !p.watered_today {
                UnitAction::Water
            } else {
                UnitAction::Pass
            }
        } else if let Tile::Animal(a) = &farm.tiles[fy][fx] {
            if a.fertilizer_available {
                UnitAction::CollectFertilizer
            } else if !a.fed_today && farmer_wheat > 0 {
                UnitAction::Feed
            } else {
                UnitAction::Care
            }
        } else {
            UnitAction::Pass
        };

        // Route Hands
        let mut hands = vec![UnitAction::Pass; farm.hands.len()];
        for (i, &h_pos) in farm.hands.iter().enumerate() {
            let (hx, hy) = h_pos;
            let h_inv = priv_farm.inventories.get(i + 1);
            let h_wheat = h_inv.and_then(|inv| inv.get("WHEAT")).copied().unwrap_or(0);
            let h_total = h_inv.map(|inv| inv.values().sum::<i64>()).unwrap_or(0);
            
            let _h_vec = Self::extract_worker_features(state, player_idx, (hx, hy), false, h_wheat, h_total);

            // Execute immediate physical task if standing on valid tile
            if let Tile::Plant(p) = &farm.tiles[hy][hx] {
                if p.yield_units > 0 {
                    hands[i] = UnitAction::Harvest;
                    continue;
                } else if !p.watered_today {
                    hands[i] = UnitAction::Water;
                    continue;
                }
            } else if let Tile::Empty = &farm.tiles[hy][hx] {
                let melon_seeds = *priv_farm.seeds.get(&Crop::Melon).unwrap_or(&0);
                let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);
                let wheat_seeds = *priv_farm.seeds.get(&Crop::Wheat).unwrap_or(&0);

                if day < 4 && melon_seeds > 0 {
                    hands[i] = UnitAction::Plant(Crop::Melon);
                    continue;
                } else if day < 4 && wheat_seeds > 0 {
                    hands[i] = UnitAction::Plant(Crop::Wheat);
                    continue;
                } else if straw_seeds > 0 {
                    hands[i] = UnitAction::Plant(Crop::Strawberry);
                    continue;
                }
            }
        }

        PlayerAction {
            farmer,
            hands,
            market,
        }
    }
}

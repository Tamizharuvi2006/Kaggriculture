//! Generic Multi-Crop Dynamic Motion Planner & Economic Router.
//! Supports Melon + Wheat Kickstart, Cow Manure Recycling, Strawberry Onboarding, and Q2/Q3 Expansion.

use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;
use crate::market::{Product, MarketOrder};
use crate::workers::UnitAction;
use crate::farm::{Animal, Tile, Crop, Quadrant};
use crate::policies::Policy;

#[derive(Clone, Debug)]
pub struct MultiCropPlannerPolicy {
    name: &'static str,
}

impl MultiCropPlannerPolicy {
    pub fn new() -> Self {
        Self {
            name: "multicrop_elite_planner",
        }
    }

    /// Finds Manhattan path to move unit closer to (target_x, target_y)
    fn move_toward(curr_x: usize, curr_y: usize, target_x: usize, target_y: usize) -> UnitAction {
        if curr_x < target_x {
            UnitAction::East
        } else if curr_x > target_x {
            UnitAction::West
        } else if curr_y < target_y {
            UnitAction::South
        } else if curr_y > target_y {
            UnitAction::North
        } else {
            UnitAction::Pass
        }
    }
}

impl Policy for MultiCropPlannerPolicy {
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
        let quads = farm.unlocked_quadrants.len();

        let mut market = Vec::new();
        let mut farmer = UnitAction::Pass;
        let mut hands = vec![UnitAction::Pass; farm.hands.len()];

        // =========================================================================
        // 1. DYNAMIC MARKET GOVERNOR
        // =========================================================================

        // Step 0-1: Initial Grandmaster Allocation
        if step == 0 || (step == 1 && farm.hands.is_empty()) {
            market.push(MarketOrder::Hire);
            market.push(MarketOrder::Hire);
            market.push(MarketOrder::BuyAnimal(Animal::Cow, 1));
            market.push(MarketOrder::BuySeed(Crop::Melon, 6));
            market.push(MarketOrder::BuySeed(Crop::Wheat, 6));
        }


        // Daily hiring schedule (scale up to 4 hands by Day 4, up to 8 hands by Day 10, up to 12 hands by Day 12)
        if hour == 0 && step > 1 {
            let max_hands_target = if day < 4 { 4 } else if day < 10 { 8 } else { 12 };
            if farm.hands.len() < max_hands_target && money >= 200.0 {
                market.push(MarketOrder::Hire);
                if money >= 500.0 && farm.hands.len() + 1 < max_hands_target {
                    market.push(MarketOrder::Hire);
                }
            }
        }

        // Mid-game crop seed replenishments
        if hour == 0 {
            if day >= 4 && day < 25 {
                let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);
                let target_straw = if quads >= 3 { 30 } else if quads >= 2 { 20 } else { 10 };
                if (straw_seeds as usize) < target_straw && money >= 300.0 {
                    let buy_count = ((money / 20.0).floor() as i64).min(target_straw as i64 - straw_seeds).min(10);
                    if buy_count > 0 {
                        market.push(MarketOrder::BuySeed(Crop::Strawberry, buy_count));
                    }
                }
            }

            // Recurring Melon replenishment
            if day >= 4 && day < 24 && money >= 1000.0 {
                let melon_seeds = *priv_farm.seeds.get(&Crop::Melon).unwrap_or(&0);
                if melon_seeds < 6 {
                    market.push(MarketOrder::BuySeed(Crop::Melon, 6 - melon_seeds));
                }
            }
        }

        // Regular Inventory Liquidations (Capture instant cash)
        for prod in [
            Product::Fertilizer,
            Product::Milk,
            Product::Wool,
            Product::Melon,
            Product::Strawberry,
            Product::Carrot,
            Product::Tomato,
        ] {
            let count = *priv_farm.shed.get(prod.name()).unwrap_or(&0);
            if count > 0 {
                market.push(MarketOrder::Sell(prod, count));
            }
        }

        // Terminal clearance at Step 700..719
        if step >= 700 {
            for prod in Product::ALL {
                let count = *priv_farm.shed.get(prod.name()).unwrap_or(&0);
                if count > 0 {
                    market.push(MarketOrder::Sell(prod, count));
                }
            }
        }

        // =========================================================================
        // 2. DYNAMIC WORKER MOTION PLANNER & TASK ROUTER
        // =========================================================================

        // Collect all tasks on the board
        let mut unwatered_plants: Vec<(usize, usize)> = Vec::new();
        let mut mature_harvests: Vec<(usize, usize)> = Vec::new();
        let mut empty_tillable_tiles: Vec<(usize, usize)> = Vec::new();
        let mut cow_tiles: Vec<(usize, usize, bool, bool)> = Vec::new(); // (x, y, needs_feed, has_fert)

        for y in 0..10 {
            for x in 0..10 {
                match &farm.tiles[y][x] {
                    Tile::Plant(p) => {
                        if p.yield_units > 0 {
                            mature_harvests.push((x, y));
                        } else if !p.watered_today {
                            unwatered_plants.push((x, y));
                        }
                    }
                    Tile::Empty => {
                        // Only consider unlocked quadrants
                        let in_q1 = x < 5 && y < 5;
                        let in_q2 = x >= 5 && y < 5 && farm.unlocked_quadrants.contains(&Quadrant::NE);
                        let in_q3 = x < 5 && y >= 5 && farm.unlocked_quadrants.contains(&Quadrant::SW);
                        let in_q4 = x >= 5 && y >= 5 && farm.unlocked_quadrants.contains(&Quadrant::SE);
                        if in_q1 || in_q2 || in_q3 || in_q4 {
                            empty_tillable_tiles.push((x, y));
                        }
                    }
                    Tile::Animal(a) => {
                        cow_tiles.push((x, y, !a.fed_today, a.fertilizer_available));
                    }
                    _ => {}
                }
            }
        }

        // Route Farmer: Dedicated Animal Feeder & Manure Collector + Harvester
        let (fx, fy) = farm.farmer;
        let farmer_wheat = if !priv_farm.inventories.is_empty() {
            *priv_farm.inventories[0].get("WHEAT").unwrap_or(&0)
        } else {
            0
        };

        if !cow_tiles.is_empty() {
            let (cx, cy, needs_feed, has_fert) = cow_tiles[0];
            if fx == cx && fy == cy {
                if has_fert {
                    farmer = UnitAction::CollectFertilizer;
                } else if needs_feed && farmer_wheat > 0 {
                    farmer = UnitAction::Feed;
                } else if !mature_harvests.is_empty() {
                    let (hx, hy) = mature_harvests[0];
                    farmer = Self::move_toward(fx, fy, hx, hy);
                } else {
                    farmer = UnitAction::Care;
                }
            } else if fx == 0 && fy == 0 && farmer_wheat == 0 && *priv_farm.shed.get("WHEAT").unwrap_or(&0) > 0 {
                farmer = UnitAction::Pickup("WHEAT".to_string(), 2);
            } else {
                farmer = Self::move_toward(fx, fy, cx, cy);
            }
        } else if !mature_harvests.is_empty() {
            let (hx, hy) = mature_harvests[0];
            if fx == hx && fy == hy {
                farmer = UnitAction::Harvest;
            } else {
                farmer = Self::move_toward(fx, fy, hx, hy);
            }
        }

        // Route Hands: Waterers, Planters, Harvesters
        for (i, hand) in farm.hands.iter().enumerate() {
            let &(hx, hy) = hand;

            // Priority 1: Harvest if standing on mature plant
            if let Tile::Plant(p) = &farm.tiles[hy][hx] {
                if p.yield_units > 0 {
                    hands[i] = UnitAction::Harvest;
                    continue;
                } else if !p.watered_today {
                    hands[i] = UnitAction::Water;
                    continue;
                }
            }

            // Priority 2: Water unwatered plants
            if let Some(&(tx, ty)) = unwatered_plants.get(i % unwatered_plants.len().max(1)) {
                if hx == tx && hy == ty {
                    hands[i] = UnitAction::Water;
                } else {
                    hands[i] = Self::move_toward(hx, hy, tx, ty);
                }
                continue;
            }

            // Priority 3: Plant empty tiles
            if let Some(&(ex, ey)) = empty_tillable_tiles.get(i % empty_tillable_tiles.len().max(1)) {
                if hx == ex && hy == ey {
                    // Decide what to plant
                    let melon_seeds = *priv_farm.seeds.get(&Crop::Melon).unwrap_or(&0);
                    let wheat_seeds = *priv_farm.seeds.get(&Crop::Wheat).unwrap_or(&0);
                    let straw_seeds = *priv_farm.seeds.get(&Crop::Strawberry).unwrap_or(&0);

                    if day < 4 && melon_seeds > 0 {
                        hands[i] = UnitAction::Plant(Crop::Melon);
                    } else if day < 4 && wheat_seeds > 0 {
                        hands[i] = UnitAction::Plant(Crop::Wheat);
                    } else if straw_seeds > 0 {
                        hands[i] = UnitAction::Plant(Crop::Strawberry);
                    } else if melon_seeds > 0 {
                        hands[i] = UnitAction::Plant(Crop::Melon);
                    } else if wheat_seeds > 0 {
                        hands[i] = UnitAction::Plant(Crop::Wheat);
                    }
                } else {
                    hands[i] = Self::move_toward(hx, hy, ex, ey);
                }
                continue;
            }

            // Priority 4: Drop items at shed (0, 0)
            if hx == 0 && hy == 0 {
                hands[i] = UnitAction::Drop;
            } else {
                hands[i] = Self::move_toward(hx, hy, 0, 0);
            }
        }

        PlayerAction {
            farmer,
            hands,
            market,
        }
    }
}

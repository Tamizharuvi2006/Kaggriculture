use crate::engine::state::GameState;
use crate::engine::rules::{fib_cost, get_shop_products, ALL_SHOP_NAMES};
use crate::farm::{Animal, Quadrant, Tile, is_shed_adjacent, shed_access_tiles, default_spawn};
use crate::market::{Product, MarketOrder, calculate_market_price};
use crate::workers::UnitAction;
use crate::rng::PythonRng;
use std::collections::HashMap;

#[derive(Clone, Debug, Default)]
pub struct PlayerAction {
    pub farmer: UnitAction,
    pub hands: Vec<UnitAction>,
    pub market: Vec<MarketOrder>,
}

pub fn step_game(state: &mut GameState, actions: &[PlayerAction; 2]) {
    if state.done {
        return;
    }

    let board_size = state.board_size;
    let turns_per_day = state.turns_per_day;
    let shed_capacity = state.shed_capacity;
    let current_step = state.step;
    let current_day = current_step / turns_per_day;

    // 1. Process Worker Actions for both players
    for p_idx in 0..2 {
        let act = &actions[p_idx];

        // Atomic PLANT validation: count total plant demand for each crop this turn
        let mut plant_demand = HashMap::new();
        if let UnitAction::Plant(c) = act.farmer {
            *plant_demand.entry(c).or_insert(0) += 1;
        }
        for h_act in &act.hands {
            if let UnitAction::Plant(c) = h_act {
                *plant_demand.entry(*c).or_insert(0) += 1;
            }
        }

        let mut blocked_crops = Vec::new();
        for (crop, count) in plant_demand {
            let available = *state.privates[p_idx].seeds.get(&crop).unwrap_or(&0);
            if count > available {
                blocked_crops.push(crop);
            }
        }

        let sanitize_action = |a: &UnitAction| -> UnitAction {
            if let UnitAction::Plant(c) = a {
                if blocked_crops.contains(c) {
                    return UnitAction::Pass;
                }
            }
            a.clone()
        };

        // Apply farmer action (index 0)
        let farmer_act = sanitize_action(&act.farmer);
        apply_unit_action(
            &mut state.farms[p_idx],
            &mut state.privates[p_idx],
            0,
            &farmer_act,
            board_size,
            current_day as i32,
            turns_per_day as i32,
            shed_capacity as i64,
        );

        // Apply hands actions (index 1+)
        for (h_idx, raw_h_act) in act.hands.iter().enumerate() {
            let hand_act = sanitize_action(raw_h_act);
            apply_unit_action(
                &mut state.farms[p_idx],
                &mut state.privates[p_idx],
                h_idx + 1,
                &hand_act,
                board_size,
                current_day as i32,
                turns_per_day as i32,
                shed_capacity as i64,
            );
        }
    }

    // 2. Process Market Orders
    process_market(state, actions);

    // 3. Town Consumption
    town_consume(state, current_step);

    // 4. Plant Decay
    for p_idx in 0..2 {
        decay_plants(&mut state.farms[p_idx], current_step as i32);
    }

    // 5. End of Day Refresh
    if (current_step + 1) % turns_per_day == 0 {
        end_of_day(state, current_day);
    }

    // Advance Step Counter
    let next_step = current_step + 1;
    state.step = next_step;
    state.day = next_step / turns_per_day;
    state.hour = next_step % turns_per_day;

    if current_step >= state.episode_steps - 2 {
        state.done = true;
        state.rewards = [state.farms[0].money, state.farms[1].money];
    }
}

fn apply_unit_action(
    farm: &mut crate::farm::Farm,
    private: &mut crate::workers::PrivateState,
    unit_idx: usize,
    action: &UnitAction,
    board_size: usize,
    day: i32,
    turns_per_day: i32,
    shed_capacity: i64,
) {
    let (fx, fy) = if unit_idx == 0 {
        farm.farmer
    } else if unit_idx - 1 < farm.hands.len() {
        farm.hands[unit_idx - 1]
    } else {
        return;
    };

    match action {
        UnitAction::Pass => {}
        UnitAction::North => {
            if fy > 0 {
                set_unit_pos(farm, unit_idx, (fx, fy - 1));
            }
        }
        UnitAction::South => {
            if fy + 1 < board_size {
                set_unit_pos(farm, unit_idx, (fx, fy + 1));
            }
        }
        UnitAction::East => {
            if fx + 1 < board_size {
                set_unit_pos(farm, unit_idx, (fx + 1, fy));
            }
        }
        UnitAction::West => {
            if fx > 0 {
                set_unit_pos(farm, unit_idx, (fx - 1, fy));
            }
        }
        UnitAction::Drop => {
            if is_shed_adjacent(fx, fy, board_size) {
                let inv = private.farmer_inventory_mut(unit_idx);
                let items: Vec<(String, i64)> = inv.drain().collect();
                for (item, n) in items {
                    if n <= 0 { continue; }
                    let current_shed: i64 = private.shed.values().sum();
                    let room = (shed_capacity - current_shed).max(0);
                    let take = n.min(room);
                    if take > 0 {
                        *private.shed.entry(item).or_insert(0) += take;
                    }
                }
            }
        }
        UnitAction::Pickup(item, requested_n) => {
            if is_shed_adjacent(fx, fy, board_size) && *requested_n > 0 {
                let available = *private.shed.get(item).unwrap_or(&0);
                let take = (*requested_n).min(available);
                if take > 0 {
                    *private.shed.get_mut(item).unwrap() -= take;
                    let inv = private.farmer_inventory_mut(unit_idx);
                    *inv.entry(item.clone()).or_insert(0) += take;
                }
            }
        }
        UnitAction::Place(item, requested_n) => {
            let tile = &farm.tiles[fy][fx];
            if let Some(animal) = Animal::from_name(item) {
                if let Tile::PastureStructure = tile {
                    let inv = private.farmer_inventory_mut(unit_idx);
                    if let Some(count) = inv.get_mut(item) {
                        if *count >= 1 {
                            *count -= 1;
                            if *count == 0 { inv.remove(item); }
                            farm.tiles[fy][fx] = Tile::new_animal(animal, day);
                            return;
                        }
                    }
                } else if let Tile::CoopStructure = tile {
                    let inv = private.farmer_inventory_mut(unit_idx);
                    if let Some(count) = inv.get_mut(item) {
                        if *count >= 1 {
                            *count -= 1;
                            if *count == 0 { inv.remove(item); }
                            farm.tiles[fy][fx] = Tile::new_animal(animal, day);
                            return;
                        }
                    }
                }
            }

            // Shed drop path
            if is_shed_adjacent(fx, fy, board_size) && *requested_n > 0 {
                let current_in_inv = *private.farmer_inventory_mut(unit_idx).get(item).unwrap_or(&0);
                let current_shed: i64 = private.shed.values().sum();
                let room = (shed_capacity - current_shed).max(0);
                let take = (*requested_n).min(current_in_inv).min(room);
                if take > 0 {
                    let inv = private.farmer_inventory_mut(unit_idx);
                    *inv.get_mut(item).unwrap() -= take;
                    if *inv.get(item).unwrap() == 0 { inv.remove(item); }
                    *private.shed.entry(item.clone()).or_insert(0) += take;
                }
            }
        }
        UnitAction::Plant(crop) => {
            let tile = &farm.tiles[fy][fx];
            if tile.is_empty() {
                let seeds = private.seeds.entry(*crop).or_insert(0);
                if *seeds > 0 {
                    *seeds -= 1;
                    farm.tiles[fy][fx] = Tile::new_plant(*crop, day, turns_per_day);
                }
            }
        }
        UnitAction::Water => {
            if let Tile::Plant(ref mut plant) = farm.tiles[fy][fx] {
                if !plant.watered_today {
                    plant.watered_today = true;
                    if !plant.crop.is_ongoing() {
                        let age = day - plant.planted_day;
                        let window_start = (plant.crop.max_yield_day() + 1) / 2;
                        if age >= window_start && age <= plant.crop.max_yield_day() {
                            let bonus = if plant.fertilized_until_day >= day { 2 } else { 1 };
                            plant.yield_units = (plant.yield_units + bonus).min(plant.crop.max_yield());
                        }
                    }
                }
            }
        }
        UnitAction::Harvest => {
            match &mut farm.tiles[fy][fx] {
                Tile::Plant(plant) => {
                    if plant.yield_units > 0 && day - plant.planted_day >= plant.crop.first_yield_day() {
                        let units = plant.yield_units;
                        plant.yield_units = 0;
                        let is_ongoing = plant.crop.is_ongoing();
                        let crop_name = plant.crop.name().to_string();
                        let inv = private.farmer_inventory_mut(unit_idx);
                        *inv.entry(crop_name).or_insert(0) += units as i64;
                        if !is_ongoing {
                            farm.tiles[fy][fx] = Tile::Empty;
                        }
                    }
                }
                Tile::Animal(animal) => {
                    if animal.yield_units > 0 {
                        let units = animal.yield_units;
                        animal.yield_units = 0;
                        let prod_name = animal.animal.product_name().to_string();
                        let inv = private.farmer_inventory_mut(unit_idx);
                        *inv.entry(prod_name).or_insert(0) += units as i64;
                    }
                }
                _ => {}
            }
        }
        UnitAction::Fertilize => {
            if let Tile::Plant(ref mut plant) = farm.tiles[fy][fx] {
                let inv = private.farmer_inventory_mut(unit_idx);
                let has_fert = match inv.get_mut("FERTILIZER") {
                    Some(c) if *c > 0 => {
                        *c -= 1;
                        Some(*c == 0)
                    }
                    _ => None,
                };
                if let Some(removed) = has_fert {
                    if removed { inv.remove("FERTILIZER"); }
                    plant.fertilized_until_day = plant.fertilized_until_day.max(day + 2);
                }
            }
        }
        UnitAction::Dig => {
            let tile = &farm.tiles[fy][fx];
            match tile {
                Tile::Empty => {}
                Tile::Animal(_) => {}
                Tile::Locked => {}
                _ => { farm.tiles[fy][fx] = Tile::Empty; }
            }
        }
        UnitAction::BuildCoop => {
            if farm.tiles[fy][fx].is_empty() {
                farm.tiles[fy][fx] = Tile::CoopStructure;
            }
        }
        UnitAction::BuildPasture => {
            if farm.tiles[fy][fx].is_empty() {
                farm.tiles[fy][fx] = Tile::PastureStructure;
            }
        }
        UnitAction::Feed => {
            if let Tile::Animal(ref mut animal) = farm.tiles[fy][fx] {
                if !animal.fed_today {
                    let inv = private.farmer_inventory_mut(unit_idx);
                    let mut ok = false;
                    if let Some(c) = inv.get_mut("WHEAT") {
                        if *c > 0 {
                            *c -= 1;
                            if *c == 0 { inv.remove("WHEAT"); }
                            ok = true;
                        }
                    }
                    if ok {
                        animal.fed_today = true;
                    }
                }
            }
        }
        UnitAction::CollectFertilizer => {
            if let Tile::Animal(ref mut animal) = farm.tiles[fy][fx] {
                if animal.fertilizer_available {
                    animal.fertilizer_available = false;
                    let inv = private.farmer_inventory_mut(unit_idx);
                    *inv.entry("FERTILIZER".to_string()).or_insert(0) += 1;
                }
            }
        }
        UnitAction::Care => {
            if let Tile::Animal(ref mut animal) = farm.tiles[fy][fx] {
                if !animal.cared_today {
                    animal.cared_today = true;
                }
            }
        }
    }
}

fn set_unit_pos(farm: &mut crate::farm::Farm, idx: usize, pos: (usize, usize)) {
    if idx == 0 {
        farm.farmer = pos;
    } else if idx - 1 < farm.hands.len() {
        farm.hands[idx - 1] = pos;
    }
}

fn spawn_hand(farm: &crate::farm::Farm, board_size: usize) -> (usize, usize) {
    let access = shed_access_tiles(board_size);
    let mut occ = [0usize; 4];
    for (i, tile) in access.iter().enumerate() {
        if farm.farmer == *tile { occ[i] += 1; }
        for h in &farm.hands {
            if *h == *tile { occ[i] += 1; }
        }
    }
    let mut best_idx = 0;
    let mut min_occ = occ[0];
    for i in 1..4 {
        if occ[i] < min_occ {
            min_occ = occ[i];
            best_idx = i;
        }
    }
    access[best_idx]
}

fn process_market(state: &mut GameState, actions: &[PlayerAction; 2]) {
    let board_size = state.board_size;
    let shed_capacity = state.shed_capacity as i64;

    let order_queues = [
        &actions[0].market,
        &actions[1].market,
    ];
    let mut q_indices = [0usize, 0usize];
    let mut order_states: [Option<MarketOrder>; 2] = [None, None];

    loop {
        // 1. Pop from queue if player has no active order
        for p_idx in 0..2 {
            if order_states[p_idx].is_none() && q_indices[p_idx] < order_queues[p_idx].len() {
                order_states[p_idx] = Some(order_queues[p_idx][q_indices[p_idx]].clone());
                q_indices[p_idx] += 1;
            }
        }

        if order_states[0].is_none() && order_states[1].is_none() {
            break;
        }

        // 2. Atomic orders: HIRE and BUY_LAND (P0 then P1)
        let mut atomic_committed = false;
        for p_idx in 0..2 {
            if let Some(ref o) = order_states[p_idx] {
                match o {
                    MarketOrder::Hire => {
                        let cost = fib_cost(state.farms[p_idx].hires_today) as f64;
                        if state.farms[p_idx].money >= cost {
                            state.farms[p_idx].money -= cost;
                            state.farms[p_idx].hires_today += 1;
                            let hand_pos = spawn_hand(&state.farms[p_idx], board_size);
                            state.farms[p_idx].hands.push(hand_pos);
                            state.privates[p_idx].inventories.push(HashMap::new());
                        }
                        order_states[p_idx] = None;
                        atomic_committed = true;
                    }
                    MarketOrder::BuyLand => {
                        let n_unlocked = state.farms[p_idx].unlocked_quadrants.len() - 1;
                        if n_unlocked < Quadrant::LAND_ORDER.len() {
                            let cost = Quadrant::LAND_PRICES[n_unlocked] as f64;
                            if state.farms[p_idx].money >= cost {
                                state.farms[p_idx].money -= cost;
                                let quad = Quadrant::LAND_ORDER[n_unlocked];
                                state.farms[p_idx].unlocked_quadrants.push(quad);
                                for y in 0..board_size {
                                    for x in 0..board_size {
                                        if Quadrant::of(x, y, board_size) == quad && state.farms[p_idx].tiles[y][x].is_locked() {
                                            state.farms[p_idx].tiles[y][x] = Tile::Empty;
                                        }
                                    }
                                }
                            }
                        }
                        order_states[p_idx] = None;
                        atomic_committed = true;
                    }
                    _ => {}
                }
            }
        }

        if atomic_committed {
            continue;
        }

        // 3. Per-unit lockstep loop for commodities, seeds, animals
        let mut quoted = [None, None];
        for p_idx in 0..2 {
            if let Some(ref o) = order_states[p_idx] {
                match o {
                    MarketOrder::Sell(prod, rem) if *rem > 0 => {
                        let inv = *state.market.inventory.get(prod).unwrap_or(&10000);
                        let price = calculate_market_price(*prod, inv);
                        quoted[p_idx] = Some((*prod, price));
                    }
                    MarketOrder::BuyProduct(prod, rem) if *rem > 0 => {
                        let inv = *state.market.inventory.get(prod).unwrap_or(&10000);
                        let price = calculate_market_price(*prod, inv - 1);
                        quoted[p_idx] = Some((*prod, price));
                    }
                    MarketOrder::BuySeed(crop, rem) if *rem > 0 => {
                        quoted[p_idx] = Some((Product::from_name(crop.name()).unwrap(), crop.seed_cost()));
                    }
                    MarketOrder::BuyAnimal(animal, rem) if *rem > 0 => {
                        quoted[p_idx] = Some((Product::from_name(animal.product_name()).unwrap(), animal.cost()));
                    }
                    _ => { order_states[p_idx] = None; }
                }
            }
        }

        if quoted[0].is_none() && quoted[1].is_none() {
            order_states[0] = None;
            order_states[1] = None;
            continue;
        }

        let mut committed_any = false;
        for p_idx in 0..2 {
            if let Some((_prod, price)) = quoted[p_idx] {
                let mut ok = false;
                if let Some(ref mut o) = order_states[p_idx] {
                    match o {
                        MarketOrder::Sell(p, rem) => {
                            let available = *state.privates[p_idx].shed.get(p.name()).unwrap_or(&0);
                            if available > 0 {
                                *state.privates[p_idx].shed.get_mut(p.name()).unwrap() -= 1;
                                state.farms[p_idx].money += price as f64;
                                if price > 1 {
                                    *state.market.inventory.entry(*p).or_insert(10000) += 1;
                                }
                                *rem -= 1;
                                ok = true;
                            }
                        }
                        MarketOrder::BuyProduct(p, rem) => {
                            let shed_count: i64 = state.privates[p_idx].shed.values().sum();
                            if state.farms[p_idx].money >= price as f64 && shed_count < shed_capacity {
                                state.farms[p_idx].money -= price as f64;
                                *state.privates[p_idx].shed.entry(p.name().to_string()).or_insert(0) += 1;
                                *state.market.inventory.entry(*p).or_insert(10000) -= 1;
                                *rem -= 1;
                                ok = true;
                            }
                        }
                        MarketOrder::BuySeed(crop, rem) => {
                            if state.farms[p_idx].money >= price as f64 {
                                state.farms[p_idx].money -= price as f64;
                                *state.privates[p_idx].seeds.entry(*crop).or_insert(0) += 1;
                                *rem -= 1;
                                ok = true;
                            }
                        }
                        MarketOrder::BuyAnimal(animal, rem) => {
                            let shed_count: i64 = state.privates[p_idx].shed.values().sum();
                            if state.farms[p_idx].money >= price as f64 && shed_count < shed_capacity {
                                state.farms[p_idx].money -= price as f64;
                                *state.privates[p_idx].shed.entry(animal.name().to_string()).or_insert(0) += 1;
                                *rem -= 1;
                                ok = true;
                            }
                        }
                        _ => {}
                    }
                    if o.remaining() <= 0 {
                        order_states[p_idx] = None;
                    }
                }
                if ok {
                    committed_any = true;
                } else {
                    order_states[p_idx] = None;
                }
            }
        }

        if !committed_any {
            order_states[0] = None;
            order_states[1] = None;
        }
    }

    state.market.refresh_prices();
}

fn town_consume(state: &mut GameState, step: usize) {
    if step % 4 == 0 {
        for shop in &state.town.unlocked_shops {
            let products = get_shop_products(shop);
            let mult = if products.len() == 1 { 2 } else { 1 };
            for p in products {
                *state.market.inventory.entry(*p).or_insert(10000) -= mult;
            }
        }
    }
    if step % 24 == 0 {
        for p in Product::ALL {
            if p != Product::Fertilizer {
                *state.market.inventory.entry(p).or_insert(10000) -= 1;
            }
        }
    }
    state.market.refresh_prices();
}

fn decay_plants(farm: &mut crate::farm::Farm, step: i32) {
    let board_size = farm.tiles.len();
    for y in 0..board_size {
        for x in 0..board_size {
            if let Tile::Plant(ref mut plant) = farm.tiles[y][x] {
                let mls = plant.max_lifespan_step;
                if mls >= 0 && step >= mls && (step - mls) % 2 == 0 {
                    plant.yield_units -= 1;
                    if plant.yield_units <= 0 {
                        farm.tiles[y][x] = Tile::Weed;
                    }
                }
            }
        }
    }
}

fn end_of_day(state: &mut GameState, day: usize) {
    let board_size = state.board_size;
    let turns_per_day = state.turns_per_day as i32;
    let shed_cap = state.shed_capacity as i64;
    let seed = state.seed;

    let mut rng = PythonRng::new((seed.wrapping_mul(1_000_003)) ^ (day as u64));

    for p_idx in 0..2 {
        // Daily refresh plants
        for y in 0..board_size {
            for x in 0..board_size {
                if let Tile::Plant(ref mut plant) = state.farms[p_idx].tiles[y][x] {
                    let was_watered = plant.watered_today;
                    if was_watered {
                        plant.consecutive_unwatered = 0;
                    } else {
                        plant.consecutive_unwatered += 1;
                    }
                    plant.watered_today = false;
                    if plant.consecutive_unwatered >= 2 {
                        state.farms[p_idx].tiles[y][x] = Tile::Weed;
                        continue;
                    }
                    if plant.crop.is_ongoing() {
                        let next_day = (day + 1) as i32;
                        let days_since_first = next_day - plant.planted_day - plant.crop.first_yield_day();
                        if days_since_first >= 0 && days_since_first % plant.crop.interval() == 0 {
                            let prod_count = days_since_first / plant.crop.interval() + 1;
                            if prod_count <= plant.crop.max_yield() {
                                let fertilized = was_watered && plant.fertilized_until_day >= (day as i32);
                                plant.yield_units = (plant.yield_units + (if fertilized { 2 } else { 1 })).min(plant.crop.max_yield());
                                if prod_count == plant.crop.max_yield() {
                                    plant.max_lifespan_step = (next_day + 1) * turns_per_day;
                                }
                            }
                        }
                    }
                }
            }
        }

        // Daily refresh animals
        for y in 0..board_size {
            for x in 0..board_size {
                if let Tile::Animal(ref mut animal) = state.farms[p_idx].tiles[y][x] {
                    if animal.fed_today {
                        animal.consecutive_unfed = 0;
                    } else {
                        animal.consecutive_unfed += 1;
                    }
                    if animal.consecutive_unfed >= 2 {
                        let struct_tile = match animal.animal.structure() {
                            crate::farm::Structure::Coop => Tile::CoopStructure,
                            crate::farm::Structure::Pasture => Tile::PastureStructure,
                        };
                        state.farms[p_idx].tiles[y][x] = struct_tile;
                        continue;
                    }
                    let next_day = (day + 1) as i32;
                    let days_since_first = next_day - animal.placed_day - animal.animal.first_yield_day();
                    if days_since_first >= 0 && days_since_first % animal.animal.interval() == 0 {
                        let bonus = if animal.fed_today { animal.pending_care_bonus } else { 0 };
                        animal.yield_units = (animal.yield_units + 1 + bonus).min(animal.animal.max_held());
                        animal.pending_care_bonus = 0;
                    }
                    if animal.cared_today && animal.fed_today {
                        animal.pending_care_bonus += 1;
                    }
                    animal.fertilizer_available = true;
                    animal.fed_today = false;
                    animal.cared_today = false;
                }
            }
        }

        // Spawn weeds
        for y in 0..board_size {
            for x in 0..board_size {
                if state.farms[p_idx].tiles[y][x].is_empty() && rng.random() < 0.005 {
                    state.farms[p_idx].tiles[y][x] = Tile::Weed;
                }
            }
        }

        // Drop inventories to shed
        for inv in &mut state.privates[p_idx].inventories {
            let items: Vec<(String, i64)> = inv.drain().collect();
            for (item, n) in items {
                if n <= 0 { continue; }
                let current_shed: i64 = state.privates[p_idx].shed.values().sum();
                let room = (shed_cap - current_shed).max(0);
                let take = n.min(room);
                if take > 0 {
                    *state.privates[p_idx].shed.entry(item).or_insert(0) += take;
                }
            }
        }

        // Reset farmer & hands
        state.farms[p_idx].farmer = default_spawn(board_size);
        state.farms[p_idx].hands.clear();
        state.farms[p_idx].hires_today = 0;
        state.privates[p_idx].inventories = vec![HashMap::new()];
    }

    // Town shop unlock every 3 days (max 8)
    let next_day = day + 1;
    if next_day > 0 && next_day % 3 == 0 {
        if state.town.unlocked_shops.len() < 8 {
            let chosen = rng.choice(&ALL_SHOP_NAMES);
            state.town.unlocked_shops.push(chosen.to_string());
        }
    }
}

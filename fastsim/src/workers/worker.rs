use crate::farm::{Crop, Animal};
use crate::market::Product;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum UnitAction {
    Pass,
    North,
    South,
    East,
    West,
    Drop,
    Pickup(String, i64),
    Place(String, i64),
    Plant(Crop),
    Water,
    Harvest,
    Fertilize,
    Dig,
    BuildCoop,
    BuildPasture,
    Feed,
    CollectFertilizer,
    Care,
}

impl Default for UnitAction {
    fn default() -> Self {
        UnitAction::Pass
    }
}

impl UnitAction {
    pub fn from_json_array(arr: &[serde_json::Value]) -> Option<Self> {
        if arr.is_empty() { return Some(UnitAction::Pass); }
        let op = arr[0].as_str()?;
        match op {
            "PASS" => Some(UnitAction::Pass),
            "NORTH" => Some(UnitAction::North),
            "SOUTH" => Some(UnitAction::South),
            "EAST" => Some(UnitAction::East),
            "WEST" => Some(UnitAction::West),
            "DROP" => Some(UnitAction::Drop),
            "PICKUP" => {
                let item = arr.get(1)?.as_str()?.to_string();
                let n = arr.get(2).and_then(|v| v.as_i64()).unwrap_or(1);
                Some(UnitAction::Pickup(item, n))
            }
            "PLACE" => {
                let item = arr.get(1)?.as_str()?.to_string();
                let n = arr.get(2).and_then(|v| v.as_i64()).unwrap_or(1);
                Some(UnitAction::Place(item, n))
            }
            "PLANT" => {
                let crop_name = arr.get(1)?.as_str()?;
                let crop = Crop::from_name(crop_name)?;
                Some(UnitAction::Plant(crop))
            }
            "WATER" => Some(UnitAction::Water),
            "HARVEST" => Some(UnitAction::Harvest),
            "FERTILIZE" => Some(UnitAction::Fertilize),
            "DIG" => Some(UnitAction::Dig),
            "BUILD_COOP" => Some(UnitAction::BuildCoop),
            "BUILD_PASTURE" => Some(UnitAction::BuildPasture),
            "FEED" => Some(UnitAction::Feed),
            "COLLECT_FERTILIZER" => Some(UnitAction::CollectFertilizer),
            "CARE" => Some(UnitAction::Care),
            _ => Some(UnitAction::Pass),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct PrivateState {
    pub shed: HashMap<String, i64>,
    pub seeds: HashMap<Crop, i64>,
    pub inventories: Vec<HashMap<String, i64>>,
}

impl PrivateState {
    pub fn new() -> Self {
        let mut shed = HashMap::new();
        for p in Product::ALL { shed.insert(p.name().to_string(), 0); }
        for a in Animal::ALL { shed.insert(a.name().to_string(), 0); }

        let mut seeds = HashMap::new();
        for c in Crop::ALL { seeds.insert(c, 0); }

        Self {
            shed,
            seeds,
            inventories: vec![HashMap::new()],
        }
    }

    pub fn farmer_inventory_mut(&mut self, idx: usize) -> &mut HashMap<String, i64> {
        while self.inventories.len() <= idx {
            self.inventories.push(HashMap::new());
        }
        &mut self.inventories[idx]
    }
}

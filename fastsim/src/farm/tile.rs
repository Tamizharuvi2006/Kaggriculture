use super::crops::Crop;
use super::animals::{Animal, Structure};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct PlantTile {
    pub crop: Crop,
    pub planted_day: i32,
    pub watered_today: bool,
    pub consecutive_unwatered: i32,
    pub yield_units: i32,
    pub max_lifespan_step: i32,
    pub fertilized_until_day: i32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AnimalTile {
    pub animal: Animal,
    pub placed_day: i32,
    pub yield_units: i32,
    pub consecutive_unfed: i32,
    pub fed_today: bool,
    pub cared_today: bool,
    pub fertilizer_available: bool,
    pub pending_care_bonus: i32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum Tile {
    Locked,
    Empty,
    Weed,
    CoopStructure,
    PastureStructure,
    Plant(PlantTile),
    Animal(AnimalTile),
}

impl Tile {
    pub fn is_locked(&self) -> bool {
        matches!(self, Tile::Locked)
    }

    pub fn is_empty(&self) -> bool {
        matches!(self, Tile::Empty)
    }

    pub fn new_plant(crop: Crop, day: i32, turns_per_day: i32) -> Self {
        let is_ongoing = crop.is_ongoing();
        Tile::Plant(PlantTile {
            crop,
            planted_day: day,
            watered_today: false,
            consecutive_unwatered: 1, // planting day counts as unwatered
            yield_units: if is_ongoing { 0 } else { 1 },
            max_lifespan_step: if is_ongoing { -1 } else { (day + crop.max_yield_day() + 1) * turns_per_day },
            fertilized_until_day: -1,
        })
    }

    pub fn new_animal(animal: Animal, day: i32) -> Self {
        Tile::Animal(AnimalTile {
            animal,
            placed_day: day,
            yield_units: 0,
            consecutive_unfed: 0,
            fed_today: false,
            cared_today: false,
            fertilizer_available: false,
            pending_care_bonus: 0,
        })
    }
}

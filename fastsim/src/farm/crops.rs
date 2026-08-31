use serde::{Deserialize, Serialize};

#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Crop {
    Wheat,
    Carrot,
    Tomato,
    Strawberry,
    Melon,
}

impl Crop {
    pub const ALL: [Crop; 5] = [
        Crop::Wheat,
        Crop::Carrot,
        Crop::Tomato,
        Crop::Strawberry,
        Crop::Melon,
    ];

    pub fn name(&self) -> &'static str {
        match self {
            Crop::Wheat => "WHEAT",
            Crop::Carrot => "CARROT",
            Crop::Tomato => "TOMATO",
            Crop::Strawberry => "STRAWBERRY",
            Crop::Melon => "MELON",
        }
    }

    pub fn from_name(name: &str) -> Option<Crop> {
        match name {
            "WHEAT" => Some(Crop::Wheat),
            "CARROT" => Some(Crop::Carrot),
            "TOMATO" => Some(Crop::Tomato),
            "STRAWBERRY" => Some(Crop::Strawberry),
            "MELON" => Some(Crop::Melon),
            _ => None,
        }
    }

    pub fn seed_cost(&self) -> i64 {
        match self {
            Crop::Wheat => 10,
            Crop::Carrot => 20,
            Crop::Tomato => 50,
            Crop::Strawberry => 100,
            Crop::Melon => 80,
        }
    }

    pub fn first_yield_day(&self) -> i32 {
        match self {
            Crop::Wheat => 2,
            Crop::Carrot => 2,
            Crop::Tomato => 8,
            Crop::Strawberry => 10,
            Crop::Melon => 10,
        }
    }

    pub fn max_yield_day(&self) -> i32 {
        match self {
            Crop::Wheat => 4,
            Crop::Carrot => 3,
            Crop::Tomato => 8,
            Crop::Strawberry => 10,
            Crop::Melon => 12,
        }
    }

    pub fn interval(&self) -> i32 {
        match self {
            Crop::Wheat => 0,
            Crop::Carrot => 0,
            Crop::Tomato => 1,
            Crop::Strawberry => 2,
            Crop::Melon => 0,
        }
    }

    pub fn max_yield(&self) -> i32 {
        match self {
            Crop::Wheat => 6,
            Crop::Carrot => 4,
            Crop::Tomato => 4,
            Crop::Strawberry => 4,
            Crop::Melon => 6,
        }
    }

    pub fn is_ongoing(&self) -> bool {
        match self {
            Crop::Wheat => false,
            Crop::Carrot => false,
            Crop::Tomato => true,
            Crop::Strawberry => true,
            Crop::Melon => false,
        }
    }
}

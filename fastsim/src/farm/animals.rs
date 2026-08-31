use serde::{Deserialize, Serialize};

#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Animal {
    Goose,
    Cow,
    Sheep,
}

#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Structure {
    Coop,
    Pasture,
}

impl Animal {
    pub const ALL: [Animal; 3] = [Animal::Goose, Animal::Cow, Animal::Sheep];

    pub fn name(&self) -> &'static str {
        match self {
            Animal::Goose => "GOOSE",
            Animal::Cow => "COW",
            Animal::Sheep => "SHEEP",
        }
    }

    pub fn from_name(name: &str) -> Option<Animal> {
        match name {
            "GOOSE" => Some(Animal::Goose),
            "COW" => Some(Animal::Cow),
            "SHEEP" => Some(Animal::Sheep),
            _ => None,
        }
    }

    pub fn cost(&self) -> i64 {
        match self {
            Animal::Goose => 300,
            Animal::Cow => 400,
            Animal::Sheep => 500,
        }
    }

    pub fn structure(&self) -> Structure {
        match self {
            Animal::Goose => Structure::Coop,
            Animal::Cow => Structure::Pasture,
            Animal::Sheep => Structure::Pasture,
        }
    }

    pub fn first_yield_day(&self) -> i32 {
        match self {
            Animal::Goose => 4,
            Animal::Cow => 8,
            Animal::Sheep => 6,
        }
    }

    pub fn interval(&self) -> i32 {
        match self {
            Animal::Goose => 1,
            Animal::Cow => 2,
            Animal::Sheep => 3,
        }
    }

    pub fn max_held(&self) -> i32 {
        match self {
            Animal::Goose => 4,
            Animal::Cow => 6,
            Animal::Sheep => 6,
        }
    }

    pub fn product_name(&self) -> &'static str {
        match self {
            Animal::Goose => "EGG",
            Animal::Cow => "MILK",
            Animal::Sheep => "WOOL",
        }
    }
}

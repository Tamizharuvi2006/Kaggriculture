pub mod crops;
pub mod animals;
pub mod land;
pub mod tile;

pub use crops::Crop;
pub use animals::{Animal, Structure};
pub use land::{Quadrant, is_shed_adjacent, shed_access_tiles, default_spawn};
pub use tile::{Tile, PlantTile, AnimalTile};

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Farm {
    pub money: f64,
    pub tiles: Vec<Vec<Tile>>,
    pub farmer: (usize, usize),
    pub hands: Vec<(usize, usize)>,
    pub unlocked_quadrants: Vec<Quadrant>,
    pub hires_today: usize,
}

impl Farm {
    pub fn new(board_size: usize, starting_money: f64) -> Self {
        let mut tiles = Vec::with_capacity(board_size);
        for y in 0..board_size {
            let mut row = Vec::with_capacity(board_size);
            for x in 0..board_size {
                if Quadrant::of(x, y, board_size) == Quadrant::NW {
                    row.push(Tile::Empty);
                } else {
                    row.push(Tile::Locked);
                }
            }
            tiles.push(row);
        }

        Self {
            money: starting_money,
            tiles,
            farmer: default_spawn(board_size),
            hands: Vec::new(),
            unlocked_quadrants: vec![Quadrant::NW],
            hires_today: 0,
        }
    }
}

use serde::{Deserialize, Serialize};

#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Quadrant {
    NW,
    NE,
    SW,
    SE,
}

impl Quadrant {
    pub const LAND_ORDER: [Quadrant; 3] = [Quadrant::NE, Quadrant::SW, Quadrant::SE];
    pub const LAND_PRICES: [i64; 3] = [1000, 2000, 4000];

    pub fn name(&self) -> &'static str {
        match self {
            Quadrant::NW => "NW",
            Quadrant::NE => "NE",
            Quadrant::SW => "SW",
            Quadrant::SE => "SE",
        }
    }

    pub fn of(x: usize, y: usize, board_size: usize) -> Quadrant {
        let half = board_size / 2;
        if y < half {
            if x < half { Quadrant::NW } else { Quadrant::NE }
        } else {
            if x < half { Quadrant::SW } else { Quadrant::SE }
        }
    }

    pub fn is_initial_unlocked(&self) -> bool {
        matches!(self, Quadrant::NW)
    }
}

pub fn shed_access_tiles(board_size: usize) -> [(usize, usize); 4] {
    let half = board_size / 2;
    [
        (half - 1, half - 1),
        (half, half - 1),
        (half - 1, half),
        (half, half),
    ]
}

pub fn is_shed_adjacent(x: usize, y: usize, board_size: usize) -> bool {
    let tiles = shed_access_tiles(board_size);
    tiles.contains(&(x, y))
}

pub fn default_spawn(board_size: usize) -> (usize, usize) {
    for (x, y) in shed_access_tiles(board_size) {
        if Quadrant::of(x, y, board_size) == Quadrant::NW {
            return (x, y);
        }
    }
    (0, 0)
}

use crate::farm::Farm;
use crate::market::Market;
use crate::workers::PrivateState;
use crate::rng::PythonRng;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct TownState {
    pub unlocked_shops: Vec<String>,
}

impl TownState {
    pub fn new() -> Self {
        Self { unlocked_shops: Vec::new() }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct GameState {
    pub seed: u64,
    pub step: usize,
    pub day: usize,
    pub hour: usize,
    pub board_size: usize,
    pub turns_per_day: usize,
    pub episode_steps: usize,
    pub shed_capacity: usize,
    pub farms: [Farm; 2],
    pub privates: [PrivateState; 2],
    pub market: Market,
    pub town: TownState,
    pub done: bool,
    pub rewards: [f64; 2],
    #[serde(skip)]
    pub rng: Option<PythonRng>,
}

impl GameState {
    pub fn new(seed: u64, board_size: usize, starting_money: f64, episode_steps: usize, turns_per_day: usize, shed_capacity: usize) -> Self {
        let f0 = Farm::new(board_size, starting_money);
        let f1 = Farm::new(board_size, starting_money);
        let p0 = PrivateState::new();
        let p1 = PrivateState::new();
        let market = Market::new();
        let town = TownState::new();

        Self {
            seed,
            step: 0,
            day: 0,
            hour: 0,
            board_size,
            turns_per_day,
            episode_steps,
            shed_capacity,
            farms: [f0, f1],
            privates: [p0, p1],
            market,
            town,
            done: false,
            rewards: [0.0, 0.0],
            rng: Some(PythonRng::new(seed)),
        }
    }
}

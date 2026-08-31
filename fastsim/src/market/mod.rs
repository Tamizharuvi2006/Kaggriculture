pub mod prices;
pub mod orders;

pub use prices::{Product, calculate_market_price, default_market_params, MARKET_I0, PRICE_FLOOR};
pub use orders::MarketOrder;

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Market {
    pub inventory: HashMap<Product, i64>,
    pub prices: HashMap<Product, i64>,
}

impl Market {
    pub fn new() -> Self {
        let mut inventory = HashMap::new();
        let mut prices = HashMap::new();
        for p in Product::ALL {
            inventory.insert(p, MARKET_I0);
            prices.insert(p, calculate_market_price(p, MARKET_I0));
        }
        Self { inventory, prices }
    }

    pub fn refresh_prices(&mut self) {
        for p in Product::ALL {
            let inv = *self.inventory.get(&p).unwrap_or(&MARKET_I0);
            self.prices.insert(p, calculate_market_price(p, inv));
        }
    }
}

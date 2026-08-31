use crate::farm::Crop;
use crate::farm::Animal;
use crate::market::prices::Product;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum MarketOrder {
    Hire,
    BuyLand,
    BuySeed(Crop, i64),
    BuyProduct(Product, i64),
    BuyAnimal(Animal, i64),
    Sell(Product, i64),
}

impl MarketOrder {
    pub fn remaining(&self) -> i64 {
        match self {
            MarketOrder::Hire | MarketOrder::BuyLand => 1,
            MarketOrder::BuySeed(_, rem)
            | MarketOrder::BuyProduct(_, rem)
            | MarketOrder::BuyAnimal(_, rem)
            | MarketOrder::Sell(_, rem) => *rem,
        }
    }

    pub fn from_json_array(arr: &[serde_json::Value]) -> Option<Self> {
        if arr.is_empty() { return None; }
        let op = arr[0].as_str()?;
        match op {
            "HIRE" => Some(MarketOrder::Hire),
            "BUY_LAND" => Some(MarketOrder::BuyLand),
            "BUY_SEED" => {
                let crop_name = arr.get(1)?.as_str()?;
                let crop = Crop::from_name(crop_name)?;
                let count = arr.get(2).and_then(|v| v.as_i64()).unwrap_or(1);
                if count > 0 { Some(MarketOrder::BuySeed(crop, count)) } else { None }
            }
            "BUY_PRODUCT" => {
                let p_name = arr.get(1)?.as_str()?;
                let prod = Product::from_name(p_name)?;
                let count = arr.get(2).and_then(|v| v.as_i64()).unwrap_or(1);
                if count > 0 { Some(MarketOrder::BuyProduct(prod, count)) } else { None }
            }
            "BUY_ANIMAL" => {
                let a_name = arr.get(1)?.as_str()?;
                let animal = Animal::from_name(a_name)?;
                let count = arr.get(2).and_then(|v| v.as_i64()).unwrap_or(1);
                if count > 0 { Some(MarketOrder::BuyAnimal(animal, count)) } else { None }
            }
            "SELL" => {
                let p_name = arr.get(1)?.as_str()?;
                let prod = Product::from_name(p_name)?;
                let count = arr.get(2).and_then(|v| v.as_i64()).unwrap_or(1);
                if count > 0 { Some(MarketOrder::Sell(prod, count)) } else { None }
            }
            _ => None,
        }
    }
}

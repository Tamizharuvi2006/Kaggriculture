use serde::{Deserialize, Serialize};

pub const MARKET_I0: i64 = 10000;
pub const PRICE_FLOOR: i64 = 1;
pub const HINGE_GAIN: f64 = 8.0;

#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Product {
    Wheat,
    Carrot,
    Tomato,
    Strawberry,
    Melon,
    Egg,
    Milk,
    Wool,
    Fertilizer,
}

impl Product {
    pub const ALL: [Product; 9] = [
        Product::Wheat,
        Product::Carrot,
        Product::Tomato,
        Product::Strawberry,
        Product::Melon,
        Product::Egg,
        Product::Milk,
        Product::Wool,
        Product::Fertilizer,
    ];

    pub fn name(&self) -> &'static str {
        match self {
            Product::Wheat => "WHEAT",
            Product::Carrot => "CARROT",
            Product::Tomato => "TOMATO",
            Product::Strawberry => "STRAWBERRY",
            Product::Melon => "MELON",
            Product::Egg => "EGG",
            Product::Milk => "MILK",
            Product::Wool => "WOOL",
            Product::Fertilizer => "FERTILIZER",
        }
    }

    pub fn from_name(name: &str) -> Option<Product> {
        match name {
            "WHEAT" => Some(Product::Wheat),
            "CARROT" => Some(Product::Carrot),
            "TOMATO" => Some(Product::Tomato),
            "STRAWBERRY" => Some(Product::Strawberry),
            "MELON" => Some(Product::Melon),
            "EGG" => Some(Product::Egg),
            "MILK" => Some(Product::Milk),
            "WOOL" => Some(Product::Wool),
            "FERTILIZER" => Some(Product::Fertilizer),
            _ => None,
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct MarketParam {
    pub base: f64,
    pub i0: f64,
    pub t: f64,
    pub below_func: &'static str,
    pub below_target: f64,
    pub above_func: &'static str,
    pub above_target: f64,
}

pub fn default_market_params(p: Product) -> MarketParam {
    match p {
        Product::Wheat => MarketParam { base: 25.0, i0: 10000.0, t: 400.0, below_func: "sqrt", below_target: 0.80, above_func: "log", above_target: 0.20 },
        Product::Carrot => MarketParam { base: 35.0, i0: 10000.0, t: 450.0, below_func: "hinge", below_target: 1.00, above_func: "sqrt", above_target: 0.70 },
        Product::Tomato => MarketParam { base: 60.0, i0: 10000.0, t: 200.0, below_func: "hinge", below_target: 0.40, above_func: "sqrt", above_target: 0.60 },
        Product::Strawberry => MarketParam { base: 120.0, i0: 10000.0, t: 100.0, below_func: "sqrt", below_target: 0.70, above_func: "linear", above_target: 1.60 },
        Product::Melon => MarketParam { base: 250.0, i0: 10000.0, t: 300.0, below_func: "log", below_target: 0.20, above_func: "sq", above_target: 3.60 },
        Product::Egg => MarketParam { base: 50.0, i0: 10000.0, t: 332.0, below_func: "hinge", below_target: 0.40, above_func: "log", above_target: 0.20 },
        Product::Milk => MarketParam { base: 160.0, i0: 10000.0, t: 122.0, below_func: "sqrt", below_target: 0.60, above_func: "linear", above_target: 1.60 },
        Product::Wool => MarketParam { base: 200.0, i0: 10000.0, t: 105.0, below_func: "log", below_target: 0.20, above_func: "sq", above_target: 3.20 },
        Product::Fertilizer => MarketParam { base: 100.0, i0: 10000.0, t: 200.0, below_func: "linear", below_target: 0.40, above_func: "linear", above_target: 0.40 },
    }
}

pub fn shape_func(func: &str, x: f64, t: f64) -> f64 {
    let x = x.max(0.0);
    match func {
        "linear" => x,
        "sq" => x * x,
        "sqrt" => x.sqrt(),
        "log" => (1.0 + x).ln(),
        "log10" => (1.0 + x).log10(),
        "hinge" => {
            if t <= 0.0 {
                x
            } else {
                let u = x / t;
                u + HINGE_GAIN * (0.0f64).max(u - 1.0).powi(2)
            }
        }
        _ => x,
    }
}

/// Exact Python `round(x)` (Banker's Rounding: half to even)
pub fn py_round(val: f64) -> i64 {
    let floor = val.floor();
    let diff = val - floor;
    if (diff - 0.5).abs() < 1e-9 {
        let floor_i = floor as i64;
        if floor_i % 2 == 0 {
            floor_i
        } else {
            floor_i + 1
        }
    } else {
        val.round() as i64
    }
}

pub fn calculate_market_price(item: Product, inventory: i64) -> i64 {
    let p = default_market_params(item);
    let inv_f = inventory as f64;
    let base = p.base;
    let i0 = p.i0;
    let t = p.t;

    let raw_price = if inv_f < i0 {
        let f = p.below_func;
        let amp = p.below_target * base / shape_func(f, t, t);
        base + amp * shape_func(f, i0 - inv_f, t)
    } else {
        let f = p.above_func;
        let amp = p.above_target * base / shape_func(f, t, t);
        base - amp * shape_func(f, inv_f - i0, t)
    };

    let rounded = py_round(raw_price);
    rounded.max(PRICE_FLOOR)
}

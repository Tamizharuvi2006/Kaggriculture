use crate::market::Product;

pub const FIB_NUMBERS: [i64; 30] = [
    1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610,
    987, 1597, 2584, 4181, 6765, 10946, 17711, 28657, 46368, 75025,
    121393, 196418, 317811, 514229, 832040,
];

pub fn fib_cost(n_already_today: usize) -> i64 {
    if n_already_today < FIB_NUMBERS.len() {
        FIB_NUMBERS[n_already_today]
    } else {
        let mut a = 1i64;
        let mut b = 1i64;
        for _ in 0..n_already_today {
            let next = a + b;
            a = b;
            b = next;
        }
        a
    }
}

pub const SHOPS: [(&str, &[Product]); 8] = [
    ("BAKERY", &[Product::Egg, Product::Wheat]),
    ("PIZZA_SHOP", &[Product::Milk, Product::Tomato, Product::Wheat]),
    ("BRUNCH_SPOT", &[Product::Egg, Product::Wheat, Product::Strawberry]),
    ("YARN_STORE", &[Product::Wool]),
    ("ICE_CREAM_SHOP", &[Product::Strawberry, Product::Milk, Product::Wheat]),
    ("PET_CAFE", &[Product::Carrot]),
    ("SMOOTHIE_SHOP", &[Product::Strawberry, Product::Milk]),
    ("FARMERS_MARKET", &[Product::Wheat, Product::Carrot, Product::Tomato, Product::Strawberry]),
];

pub const ALL_SHOP_NAMES: [&str; 8] = [
    "BAKERY",
    "BRUNCH_SPOT",
    "FARMERS_MARKET",
    "ICE_CREAM_SHOP",
    "PET_CAFE",
    "PIZZA_SHOP",
    "SMOOTHIE_SHOP",
    "YARN_STORE",
];

pub fn get_shop_products(shop_name: &str) -> &'static [Product] {
    for (name, prods) in SHOPS.iter() {
        if *name == shop_name {
            return prods;
        }
    }
    &[]
}

//! EXP187 — Root-Cause Differential Audit: 100 Stall Seeds vs 100 Healthy Seeds.
//! Tracks exact biological, economic, and pathing variables step-by-step to find the exact divergence point.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};
use fastsim::farm::{Crop, Animal, Tile};

fn main() {
    println!("================================================================================");
    println!("EXP187 — ROOT CAUSE DIFFERENTIAL AUDIT: STALL SEEDS vs HEALTHY SEEDS");
    println!("================================================================================");

    let base_policy = AdaptiveTerminalPolicy::new();
    let opp_policy = AdaptiveTerminalPolicy::new();

    let mut stall_seeds = Vec::new();
    let mut healthy_seeds = Vec::new();

    // Identify 20 stall seeds and 20 healthy seeds from seeds 20,000..21,000
    for seed in 20000..21000 {
        let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !st.done {
            let a0 = base_policy.act(&st, 0);
            let a1 = opp_policy.act(&st, 1);
            step_game(&mut st, &[a0, a1]);
        }
        let score = st.farms[0].money;
        if score < 40000.0 && stall_seeds.len() < 20 {
            stall_seeds.push((seed, score));
        } else if score > 85000.0 && healthy_seeds.len() < 20 {
            healthy_seeds.push((seed, score));
        }
        if stall_seeds.len() >= 20 && healthy_seeds.len() >= 20 {
            break;
        }
    }

    println!("Found {} Stall Seeds (Avg Score: ${:.0})", stall_seeds.len(),
        stall_seeds.iter().map(|s| s.1).sum::<f64>() / stall_seeds.len() as f64);
    println!("Found {} Healthy Seeds (Avg Score: ${:.0})\n", healthy_seeds.len(),
        healthy_seeds.iter().map(|s| s.1).sum::<f64>() / healthy_seeds.len() as f64);

    // Detailed trace of Day 0 to Day 10 biological events
    println!("--- DIFFERENTIAL STEP AUDIT (Averaged across cohorts) ---");

    struct CohortStats {
        d0_cash_after_market: f64,
        d3_shed_wheat: f64,
        d5_cash: f64,
        d5_cows: f64,
        d5_cow_milk_total: f64,
        d10_cash: f64,
        d10_melon_harvested: f64,
        d12_unlocked_quads: f64,
    }

    fn analyze_cohort(seeds: &[(u64, f64)], base_policy: &AdaptiveTerminalPolicy, opp_policy: &AdaptiveTerminalPolicy) -> CohortStats {
        let mut stats = CohortStats {
            d0_cash_after_market: 0.0,
            d3_shed_wheat: 0.0,
            d5_cash: 0.0,
            d5_cows: 0.0,
            d5_cow_milk_total: 0.0,
            d10_cash: 0.0,
            d10_melon_harvested: 0.0,
            d12_unlocked_quads: 0.0,
        };

        for &(seed, _) in seeds {
            let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
            let mut milk_produced = 0.0;
            let mut melon_harvested = 0.0;

            while !st.done {
                let step = st.step;
                let day = st.day;
                let hour = st.hour;

                if step == 1 {
                    stats.d0_cash_after_market += st.farms[0].money;
                }
                if day == 3 && hour == 0 {
                    stats.d3_shed_wheat += *st.privates[0].shed.get("WHEAT").unwrap_or(&0) as f64;
                }
                if day == 5 && hour == 0 {
                    stats.d5_cash += st.farms[0].money;
                    let mut cows = 0.0;
                    for row in &st.farms[0].tiles {
                        for tile in row {
                            if let Tile::Animal(a) = tile {
                                if a.animal == Animal::Cow { cows += 1.0; }
                            }
                        }
                    }
                    stats.d5_cows += cows;
                    stats.d5_cow_milk_total += *st.privates[0].shed.get("MILK").unwrap_or(&0) as f64;
                }
                if day == 10 && hour == 0 {
                    stats.d10_cash += st.farms[0].money;
                }
                if day == 12 && hour == 0 {
                    stats.d12_unlocked_quads += st.farms[0].unlocked_quadrants.len() as f64;
                }

                let a0 = base_policy.act(&st, 0);
                let a1 = opp_policy.act(&st, 1);
                step_game(&mut st, &[a0, a1]);
            }
        }

        let n = seeds.len() as f64;
        stats.d0_cash_after_market /= n;
        stats.d3_shed_wheat /= n;
        stats.d5_cash /= n;
        stats.d5_cows /= n;
        stats.d5_cow_milk_total /= n;
        stats.d10_cash /= n;
        stats.d10_melon_harvested /= n;
        stats.d12_unlocked_quads /= n;
        stats
    }

    let stall_metrics = analyze_cohort(&stall_seeds, &base_policy, &opp_policy);
    let healthy_metrics = analyze_cohort(&healthy_seeds, &base_policy, &opp_policy);

    println!("{:<32} | {:<16} | {:<16} | {:<16}", "Metric", "Stall Cohort (<$40k)", "Healthy Cohort (>$85k)", "Difference (S - H)");
    println!("--------------------------------------------------------------------------------------------------");
    println!("{:<32} | ${:<15.1} | ${:<15.1} | {:<+15.1}", "Day 0 Cash (After Orders)", stall_metrics.d0_cash_after_market, healthy_metrics.d0_cash_after_market, stall_metrics.d0_cash_after_market - healthy_metrics.d0_cash_after_market);
    println!("{:<32} | {:<16.2} | {:<16.2} | {:<+16.2}", "Day 3 Shed Wheat Inventory", stall_metrics.d3_shed_wheat, healthy_metrics.d3_shed_wheat, stall_metrics.d3_shed_wheat - healthy_metrics.d3_shed_wheat);
    println!("{:<32} | ${:<15.1} | ${:<15.1} | {:<+15.1}", "Day 5 Cash", stall_metrics.d5_cash, healthy_metrics.d5_cash, stall_metrics.d5_cash - healthy_metrics.d5_cash);
    println!("{:<32} | {:<16.2} | {:<16.2} | {:<+16.2}", "Day 5 Cow Count", stall_metrics.d5_cows, healthy_metrics.d5_cows, stall_metrics.d5_cows - healthy_metrics.d5_cows);
    println!("{:<32} | {:<16.2} | {:<16.2} | {:<+16.2}", "Day 5 Milk in Shed", stall_metrics.d5_cow_milk_total, healthy_metrics.d5_cow_milk_total, stall_metrics.d5_cow_milk_total - healthy_metrics.d5_cow_milk_total);
    println!("{:<32} | ${:<15.1} | ${:<15.1} | {:<+15.1}", "Day 10 Cash", stall_metrics.d10_cash, healthy_metrics.d10_cash, stall_metrics.d10_cash - healthy_metrics.d10_cash);
    println!("{:<32} | {:<16.2} | {:<16.2} | {:<+16.2}", "Day 12 Land Unlocked (Quads)", stall_metrics.d12_unlocked_quads, healthy_metrics.d12_unlocked_quads, stall_metrics.d12_unlocked_quads - healthy_metrics.d12_unlocked_quads);
    println!("================================================================================");
}

//! EXP178 — Elite Macro-Economic Architecture Reconstruction Harness.

use fastsim::engine::state::GameState;
use fastsim::engine::step::{step_game, PlayerAction};
use fastsim::policies::{Policy, AdaptiveTerminalPolicy};
use fastsim::market::{Product, MarketOrder};
use fastsim::farm::{Animal, Tile, Crop};
use rayon::prelude::*;
use std::time::Instant;

#[derive(Copy, Clone, Debug)]
pub enum MacroArm {
    Control,
    MelonKickstartOnly,
    MelonPlusWheatSelfFeed,
    FullEliteOpening,
}

pub struct ReconstructedElitePolicy {
    base: AdaptiveTerminalPolicy,
    arm: MacroArm,
}

impl ReconstructedElitePolicy {
    pub fn new(arm: MacroArm) -> Self {
        Self {
            base: AdaptiveTerminalPolicy::new(),
            arm,
        }
    }
}

impl Policy for ReconstructedElitePolicy {
    fn name(&self) -> &'static str {
        match self.arm {
            MacroArm::Control => "control_adaptive",
            MacroArm::MelonKickstartOnly => "melon_kickstart",
            MacroArm::MelonPlusWheatSelfFeed => "melon_wheat_selffeed",
            MacroArm::FullEliteOpening => "full_elite_opening",
        }
    }

    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction {
        let mut act = self.base.act(state, player_idx);
        let step = state.step;
        let day = state.day;
        let farm = &state.farms[player_idx];
        let priv_farm = &state.privates[player_idx];
        let money = farm.money;

        if matches!(self.arm, MacroArm::Control) {
            return act;
        }

        // STAGE 1: Day 0–4 Melon Kickstart
        if step <= 24 {
            // Day 0: Inject 6 Melon seeds + 6 Wheat seeds if opening
            let melon_seeds = *priv_farm.seeds.get(&Crop::Melon).unwrap_or(&0);
            let wheat_seeds = *priv_farm.seeds.get(&Crop::Wheat).unwrap_or(&0);

            if melon_seeds < 6 && money >= 300.0 {
                act.market.push(MarketOrder::BuySeed(Crop::Melon, 6 - melon_seeds));
            }
            if wheat_seeds < 6 && money >= 50.0 {
                act.market.push(MarketOrder::BuySeed(Crop::Wheat, 6 - wheat_seeds));
            }
        }

        // Sell Mature Melons at Step 72–120
        if day >= 3 {
            let melons_in_shed = *priv_farm.shed.get("MELON").unwrap_or(&0);
            if melons_in_shed > 0 {
                act.market.push(MarketOrder::Sell(Product::Melon, melons_in_shed));
            }
        }

        // Ensure Fertilizer is sold immediately for cash velocity
        let fert_in_shed = *priv_farm.shed.get("FERTILIZER").unwrap_or(&0);
        if fert_in_shed > 0 {
            act.market.push(MarketOrder::Sell(Product::Fertilizer, fert_in_shed));
        }

        act
    }
}

fn main() {
    println!("================================================================================");
    println!("EXP178 — ELITE MACRO-ECONOMIC RECONSTRUCTION (5,000 PAIRED MATCHES / ARM)");
    println!("================================================================================");

    let arms = [
        (MacroArm::Control, "Control: AdaptiveTerminal Baseline"),
        (MacroArm::MelonKickstartOnly, "Stage 1: Day 0 Melon Kickstart (6 Melons)"),
        (MacroArm::MelonPlusWheatSelfFeed, "Stage 1+2: Melon + Wheat Self-Feed Engine"),
    ];

    let seeds: Vec<u64> = (1000..3500).collect(); // 2,500 seeds x 2 seats = 5,000 matches per arm

    for &(arm, desc) in &arms {
        let hero = ReconstructedElitePolicy::new(arm);
        let control = AdaptiveTerminalPolicy::new();
        let t0 = Instant::now();

        let mut tasks = Vec::new();
        for &seed in &seeds {
            tasks.push((seed, 0));
            tasks.push((seed, 1));
        }

        let results: Vec<(f64, f64, [f64; 6])> = tasks.into_par_iter().map(|(seed, seat)| {
            let opp_seat = 1 - seat;
            let mut state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
            let mut day_cash = [0.0; 6]; // Days 1, 4, 7, 11, 15, 30
            let check_days = [1, 4, 7, 11, 15, 29];

            while !state.done && state.step < 720 {
                let day = state.day;
                let cash = state.farms[seat].money;
                for (i, &d) in check_days.iter().enumerate() {
                    if day == d && state.hour == 0 {
                        day_cash[i] = cash;
                    }
                }

                let a_hero = hero.act(&state, seat);
                let a_opp = control.act(&state, opp_seat);
                let actions = if seat == 0 { [a_hero, a_opp] } else { [a_opp, a_hero] };
                step_game(&mut state, &actions);
            }
            day_cash[5] = state.farms[seat].money;

            (state.farms[seat].money, state.farms[opp_seat].money, day_cash)
        }).collect();

        let total = results.len();
        let mut wins = 0;
        let mut sum_hero = 0.0;
        let mut sum_ctrl = 0.0;
        let mut avg_cash = [0.0; 6];

        for (h, c, dc) in &results {
            sum_hero += h;
            sum_ctrl += c;
            for i in 0..6 { avg_cash[i] += dc[i]; }
            if *h > *c + 1.0 { wins += 1; }
        }

        for i in 0..6 { avg_cash[i] /= total as f64; }

        let elapsed = t0.elapsed().as_secs_f64();
        let mean_hero = sum_hero / total as f64;
        let mean_ctrl = sum_ctrl / total as f64;
        let wr = (wins as f64 / total as f64) * 100.0;

        println!("\n>>> {}", desc);
        println!("    Matches: {} in {:.2}s ({:.1} eps/s) | WR: {:4.1}%", total, elapsed, total as f64 / elapsed, wr);
        println!("    Terminal Reward: ${:7.1} vs Ctrl ${:7.1} (Delta: {:+6.1})", mean_hero, mean_ctrl, mean_hero - mean_ctrl);
        println!("    Cash Waterfall : D1=${:.0}, D4=${:.0}, D7=${:.0}, D11=${:.0}, D15=${:.0}, D30=${:.0}",
            avg_cash[0], avg_cash[1], avg_cash[2], avg_cash[3], avg_cash[4], avg_cash[5]
        );
    }
}

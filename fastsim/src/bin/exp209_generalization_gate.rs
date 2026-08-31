//! EXP209 — 70,000-Match Out-of-Sample Generalization Gate & Head-to-Head Duel.
//! Tests EXP208 Champion Policy vs EXP205, AdaptiveTerminal, and 5 completely unseen 1800-3000+ replay bots.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, AdaptiveTerminalPolicy, EXP205FrontierPolicy, EXP208ChampionPolicy,
    UnseenElite1800_2200, UnseenElite2200_2600, UnseenElite2600_3000,
    UnseenElite3000_BotE, UnseenElite3000_BotF
};
use rayon::prelude::*;
use std::time::Instant;

pub struct GeneralizationResult {
    pub name: &'static str,
    pub replay_id: &'static str,
    pub peak_wealth: &'static str,
    pub total: usize,
    pub hero_wins: usize,
    pub opp_wins: usize,
    pub ties: usize,
    pub hero_mean: f64,
    pub opp_mean: f64,
    pub hero_worst_5pct: f64,
    pub opp_worst_5pct: f64,
    pub hero_worst_1pct: f64,
}

pub fn run_eval_matchup<OppFactory, Opp>(
    opp_factory: OppFactory,
    name: &'static str,
    replay_id: &'static str,
    peak_wealth: &'static str,
    seeds: &[u64],
) -> GeneralizationResult
where
    OppFactory: Fn() -> Opp + Sync + Send,
    Opp: Policy + 'static,
{
    // Seat 0: Hero, Seat 1: Opponent
    let s0_res: Vec<(f64, f64)> = seeds.par_iter().map(|&seed| {
        let hero = EXP208ChampionPolicy::new();
        let opp = opp_factory();
        let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !st.done {
            let a0 = hero.act(&st, 0);
            let a1 = opp.act(&st, 1);
            step_game(&mut st, &[a0, a1]);
        }
        (st.farms[0].money, st.farms[1].money)
    }).collect();

    // Seat 0: Opponent, Seat 1: Hero
    let s1_res: Vec<(f64, f64)> = seeds.par_iter().map(|&seed| {
        let opp = opp_factory();
        let hero = EXP208ChampionPolicy::new();
        let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !st.done {
            let a0 = opp.act(&st, 0);
            let a1 = hero.act(&st, 1);
            step_game(&mut st, &[a0, a1]);
        }
        (st.farms[1].money, st.farms[0].money) // (Hero, Opp)
    }).collect();

    let mut all_hero = Vec::with_capacity(seeds.len() * 2);
    let mut all_opp = Vec::with_capacity(seeds.len() * 2);
    let mut hero_wins = 0;
    let mut opp_wins = 0;
    let mut ties = 0;

    for &(h, o) in s0_res.iter().chain(s1_res.iter()) {
        all_hero.push(h);
        all_opp.push(o);
        if h > o + 1.0 { hero_wins += 1; }
        else if o > h + 1.0 { opp_wins += 1; }
        else { ties += 1; }
    }

    let n = all_hero.len() as f64;
    let hero_mean = all_hero.iter().sum::<f64>() / n;
    let opp_mean = all_opp.iter().sum::<f64>() / n;

    all_hero.sort_by(|a, b| a.partial_cmp(b).unwrap());
    all_opp.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let hero_worst_5pct = all_hero[(n * 0.05) as usize];
    let opp_worst_5pct = all_opp[(n * 0.05) as usize];
    let hero_worst_1pct = all_hero[(n * 0.01) as usize];

    GeneralizationResult {
        name,
        replay_id,
        peak_wealth,
        total: all_hero.len(),
        hero_wins,
        opp_wins,
        ties,
        hero_mean,
        opp_mean,
        hero_worst_5pct,
        opp_worst_5pct,
        hero_worst_1pct,
    }
}

fn main() {
    println!("=========================================================================================================================");
    println!("     EXP209 — 70,000-MATCH OUT-OF-SAMPLE GENERALIZATION GATE & HEAD-TO-HEAD DUEL                                         ");
    println!("=========================================================================================================================");

    let seeds_h2h_exp205: Vec<u64> = (1100000..1105000).collect(); // 10,000 matches
    let seeds_h2h_adapt: Vec<u64> = (1105000..1110000).collect();  // 10,000 matches

    let seeds_unseen_1: Vec<u64> = (1110000..1115000).collect();   // 10,000 matches
    let seeds_unseen_2: Vec<u64> = (1115000..1120000).collect();   // 10,000 matches
    let seeds_unseen_3: Vec<u64> = (1120000..1125000).collect();   // 10,000 matches
    let seeds_unseen_4: Vec<u64> = (1125000..1130000).collect();   // 10,000 matches
    let seeds_unseen_5: Vec<u64> = (1130000..1135000).collect();   // 10,000 matches

    let t0 = Instant::now();

    println!("\n--- [PART 1] DIRECT HEAD-TO-HEAD DUELS (20,000 MATCHES) ---");
    println!("[1/7] Direct Duel: EXP208 Champion vs EXP205 Frontier (Previous Best)...");
    let r_vs_exp205 = run_eval_matchup(EXP205FrontierPolicy::new, "EXP208 vs EXP205", "Direct Duel", "Prior Best", &seeds_h2h_exp205);

    println!("[2/7] Direct Duel: EXP208 Champion vs AdaptiveTerminal Baseline...");
    let r_vs_adapt = run_eval_matchup(AdaptiveTerminalPolicy::new, "EXP208 vs Adaptive", "Control Chassis", "$80,999", &seeds_h2h_adapt);

    println!("\n--- [PART 2] OUT-OF-SAMPLE UNSEEN 1800–3000+ POPULATION (50,000 MATCHES) ---");
    println!("[3/7] Unseen 1800–2200 Bot (Replay 91279421, Peak $115,554)...");
    let r_u1 = run_eval_matchup(UnseenElite1800_2200::new, "Unseen 1800–2200", "91279421.json", "$115,554", &seeds_unseen_1);

    println!("[4/7] Unseen 2200–2600 Bot (Replay 91283859, Peak $114,495)...");
    let r_u2 = run_eval_matchup(UnseenElite2200_2600::new, "Unseen 2200–2600", "91283859.json", "$114,495", &seeds_unseen_2);

    println!("[5/7] Unseen 2600–3000 Bot (Replay 91284757, Peak $106,545)...");
    let r_u3 = run_eval_matchup(UnseenElite2600_3000::new, "Unseen 2600–3000", "91284757.json", "$106,545", &seeds_unseen_3);

    println!("[6/7] Unseen 3000+ Bot E (Replay 91288415, Peak $103,408)...");
    let r_u4 = run_eval_matchup(UnseenElite3000_BotE::new, "Unseen 3000+ Bot E", "91288415.json", "$103,408", &seeds_unseen_4);

    println!("[7/7] Unseen 3000+ Bot F (Replay 91295596, Peak $102,937)...");
    let r_u5 = run_eval_matchup(UnseenElite3000_BotF::new, "Unseen 3000+ Bot F", "91295596.json", "$102,937", &seeds_unseen_5);

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nAll 70,000 Matches Completed in {:.2}s ({:.1} matches/sec)\n", elapsed, 70000.0 / elapsed);

    println!("=========================================================================================================================");
    println!("                                   EXP209 70,000-MATCH SCORECARD                                                         ");
    println!("=========================================================================================================================");
    println!("{:<24} | {:<16} | {:<12} | {:<24} | {:<12} | {:<12} | {:<12}",
        "Opponent Matchup", "Replay Identifier", "Peak Wealth", "Win / Tie / Loss", "Hero Mean", "Opp Mean", "Net Delta");
    println!("-------------------------------------------------------------------------------------------------------------------------");

    for r in &[&r_vs_exp205, &r_vs_adapt, &r_u1, &r_u2, &r_u3, &r_u4, &r_u5] {
        let wr = (r.hero_wins as f64 / r.total as f64) * 100.0;
        let tr = (r.ties as f64 / r.total as f64) * 100.0;
        let lr = (r.opp_wins as f64 / r.total as f64) * 100.0;
        let delta = r.hero_mean - r.opp_mean;

        println!("{:<24} | {:<16} | {:<12} | {:>4.1}% / {:>3.1}% / {:>4.1}% | ${:<11.1} | ${:<11.1} | {:>+11.1}",
            r.name, r.replay_id, r.peak_wealth, wr, tr, lr, r.hero_mean, r.opp_mean, delta);
    }
    println!("-------------------------------------------------------------------------------------------------------------------------");
    let un_wins = r_u1.hero_wins + r_u2.hero_wins + r_u3.hero_wins + r_u4.hero_wins + r_u5.hero_wins;
    let un_losses = r_u1.opp_wins + r_u2.opp_wins + r_u3.opp_wins + r_u4.opp_wins + r_u5.opp_wins;
    let un_ties = r_u1.ties + r_u2.ties + r_u3.ties + r_u4.ties + r_u5.ties;
    let un_total = r_u1.total + r_u2.total + r_u3.total + r_u4.total + r_u5.total;
    println!("COMBINED UNSEEN 1800-3000+ POPULATION: {:>4.1}% Wins ({}) / {:>3.1}% Ties / {:>4.1}% Losses ({})",
        (un_wins as f64 / un_total as f64) * 100.0, un_wins,
        (un_ties as f64 / un_total as f64) * 100.0,
        (un_losses as f64 / un_total as f64) * 100.0, un_losses);
    println!("=========================================================================================================================");
}

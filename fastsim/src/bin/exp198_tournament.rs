//! EXP198 — 10,000-Match Head-to-Head Tournament & Multi-Tier Population Gate for EXP198 Alpha Opportunity Policy.

use fastsim::engine::state::GameState;
use fastsim::engine::step::step_game;
use fastsim::policies::{
    Policy, AdaptiveTerminalPolicy, EXP198AlphaPolicy, D1Policy, V41Policy, AgroHybridPolicy
};
use rayon::prelude::*;
use std::time::Instant;

#[derive(Default, Clone)]
pub struct MatchResult {
    pub seed: u64,
    pub p0_score: f64,
    pub p1_score: f64,
}

pub fn run_pair<P0: Policy, P1: Policy>(p0: &P0, p1: &P1, seed: u64) -> MatchResult {
    let mut state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let mut res = MatchResult { seed, ..Default::default() };

    while !state.done {
        let a0 = p0.act(&state, 0);
        let a1 = p1.act(&state, 1);
        step_game(&mut state, &[a0, a1]);
    }

    res.p0_score = state.farms[0].money;
    res.p1_score = state.farms[1].money;
    res
}

pub struct MatchupStats {
    pub p0_name: &'static str,
    pub p1_name: &'static str,
    pub total: usize,
    pub p0_wins: usize,
    pub p1_wins: usize,
    pub ties: usize,
    pub p0_mean: f64,
    pub p1_mean: f64,
    pub p0_median: f64,
    pub p1_median: f64,
    pub p0_worst_10pct: f64,
    pub p0_worst_5pct: f64,
    pub p0_worst_1pct: f64,
    pub p1_worst_5pct: f64,
    pub p1_worst_1pct: f64,
}

pub fn evaluate_matchup<P0: Policy, P1: Policy>(
    p0_factory: impl Fn() -> P0 + Sync + Send,
    p1_factory: impl Fn() -> P1 + Sync + Send,
    p0_name: &'static str,
    p1_name: &'static str,
    seeds: &[u64],
) -> MatchupStats {
    let results: Vec<MatchResult> = seeds.par_iter().map(|&seed| {
        let p0 = p0_factory();
        let p1 = p1_factory();
        run_pair(&p0, &p1, seed)
    }).collect();

    let n = results.len() as f64;
    let mut p0_wins = 0;
    let mut p1_wins = 0;
    let mut ties = 0;

    let mut p0_scores = Vec::with_capacity(results.len());
    let mut p1_scores = Vec::with_capacity(results.len());

    for r in &results {
        p0_scores.push(r.p0_score);
        p1_scores.push(r.p1_score);

        if r.p0_score > r.p1_score + 1.0 { p0_wins += 1; }
        else if r.p1_score > r.p0_score + 1.0 { p1_wins += 1; }
        else { ties += 1; }
    }

    let p0_mean = p0_scores.iter().sum::<f64>() / n;
    let p1_mean = p1_scores.iter().sum::<f64>() / n;

    p0_scores.sort_by(|a, b| a.partial_cmp(b).unwrap());
    p1_scores.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let p0_median = p0_scores[results.len() / 2];
    let p1_median = p1_scores[results.len() / 2];

    let p0_worst_10pct = p0_scores[(results.len() as f64 * 0.10) as usize];
    let p0_worst_5pct = p0_scores[(results.len() as f64 * 0.05) as usize];
    let p0_worst_1pct = p0_scores[(results.len() as f64 * 0.01) as usize];

    let p1_worst_5pct = p1_scores[(results.len() as f64 * 0.05) as usize];
    let p1_worst_1pct = p1_scores[(results.len() as f64 * 0.01) as usize];

    MatchupStats {
        p0_name,
        p1_name,
        total: results.len(),
        p0_wins,
        p1_wins,
        ties,
        p0_mean,
        p1_mean,
        p0_median,
        p1_median,
        p0_worst_10pct,
        p0_worst_5pct,
        p0_worst_1pct,
        p1_worst_5pct,
        p1_worst_1pct,
    }
}

pub struct TierResult {
    pub name: &'static str,
    pub elo_range: &'static str,
    pub total: usize,
    pub hero_wins: usize,
    pub opp_wins: usize,
    pub ties: usize,
    pub hero_mean: f64,
    pub opp_mean: f64,
    pub hero_worst_5pct: f64,
    pub opp_worst_5pct: f64,
}

pub fn run_tier_eval<OppFactory, Opp>(
    opp_factory: OppFactory,
    tier_name: &'static str,
    elo_range: &'static str,
    seeds: &[u64],
) -> TierResult
where
    OppFactory: Fn() -> Opp + Sync + Send,
    Opp: Policy + 'static,
{
    // Seat 0
    let s0_res: Vec<(f64, f64)> = seeds.par_iter().map(|&seed| {
        let hero = EXP198AlphaPolicy::new();
        let opp = opp_factory();
        let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !st.done {
            let a0 = hero.act(&st, 0);
            let a1 = opp.act(&st, 1);
            step_game(&mut st, &[a0, a1]);
        }
        (st.farms[0].money, st.farms[1].money)
    }).collect();

    // Seat 1
    let s1_res: Vec<(f64, f64)> = seeds.par_iter().map(|&seed| {
        let opp = opp_factory();
        let hero = EXP198AlphaPolicy::new();
        let mut st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        while !st.done {
            let a0 = opp.act(&st, 0);
            let a1 = hero.act(&st, 1);
            step_game(&mut st, &[a0, a1]);
        }
        (st.farms[1].money, st.farms[0].money)
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

    TierResult {
        name: tier_name,
        elo_range,
        total: all_hero.len(),
        hero_wins,
        opp_wins,
        ties,
        hero_mean,
        opp_mean,
        hero_worst_5pct,
        opp_worst_5pct,
    }
}

fn main() {
    println!("=========================================================================================================================");
    println!("     EXP198 — 10,000-MATCH TOURNAMENT & MULTI-TIER POPULATION GATE (EXP198 ALPHA POLICY)                                 ");
    println!("=========================================================================================================================");

    let h2h_seeds: Vec<u64> = (180000..185000).collect(); // 5,000 fresh seeds x 2 seats = 10,000 matches
    let t0 = Instant::now();

    // 1. EXP198 Alpha (Seat 0) vs Adaptive (Seat 1)
    println!("\n[1/6] EXP198-Alpha (Seat 0) vs Adaptive-Terminal (Seat 1)...");
    let stats_a_vs_a_s0 = evaluate_matchup(EXP198AlphaPolicy::new, AdaptiveTerminalPolicy::new, "EXP198-Alpha", "Adaptive", &h2h_seeds);

    // 2. Adaptive (Seat 0) vs EXP198 Alpha (Seat 1)
    println!("[2/6] Adaptive-Terminal (Seat 0) vs EXP198-Alpha (Seat 1)...");
    let stats_a_vs_a_s1 = evaluate_matchup(AdaptiveTerminalPolicy::new, EXP198AlphaPolicy::new, "Adaptive", "EXP198-Alpha", &h2h_seeds);

    let combined_a0_wins = stats_a_vs_a_s0.p0_wins + stats_a_vs_a_s1.p1_wins;
    let combined_ad_wins = stats_a_vs_a_s0.p1_wins + stats_a_vs_a_s1.p0_wins;
    let combined_ties = stats_a_vs_a_s0.ties + stats_a_vs_a_s1.ties;
    let total_h2h = h2h_seeds.len() * 2;

    let a0_win_pct = (combined_a0_wins as f64 / total_h2h as f64) * 100.0;
    let ad_win_pct = (combined_ad_wins as f64 / total_h2h as f64) * 100.0;
    let combined_delta = ((stats_a_vs_a_s0.p0_mean - stats_a_vs_a_s0.p1_mean) + (stats_a_vs_a_s1.p1_mean - stats_a_vs_a_s1.p0_mean)) / 2.0;

    println!("\n=========================================================================================================================");
    println!("                                   HEAD-TO-HEAD COMBINED SCORECARD (vs Adaptive)                                         ");
    println!("=========================================================================================================================");
    println!("EXP198-Alpha Combined Win Rate   : {:.2}% ({}/{})", a0_win_pct, combined_a0_wins, total_h2h);
    println!("Adaptive-Terminal Win Rate       : {:.2}% ({}/{})", ad_win_pct, combined_ad_wins, total_h2h);
    println!("Ties Rate                        : {:.2}% ({}/{})", (combined_ties as f64 / total_h2h as f64) * 100.0, combined_ties, total_h2h);
    println!("Net Delta Margin (Hero - Opp)    : {:+.2}", combined_delta);
    println!("EXP198 Worst 5% Floor            : ${:.1} (vs Adaptive Floor: ${:.1})", stats_a_vs_a_s0.p0_worst_5pct, stats_a_vs_a_s0.p1_worst_5pct);
    println!("EXP198 Worst 1% Floor            : ${:.1} (vs Adaptive Floor: ${:.1})", stats_a_vs_a_s0.p0_worst_1pct, stats_a_vs_a_s0.p1_worst_1pct);
    println!("=========================================================================================================================");

    // Multi-Tier Population Promotion Gate
    println!("\n--- RUNNING MULTI-TIER POPULATION PROMOTION GATE (16,000 MATCHES) ---");
    let tier_seeds: Vec<u64> = (185000..187000).collect(); // 2,000 held-out seeds x 2 seats x 4 tiers

    println!("[3/6] Evaluating Tier 1 (900–1000 Elo: V4.1 Clones)...");
    let t1 = run_tier_eval(V41Policy::new, "Tier 1: Core Clones", "900–1000", &tier_seeds);

    println!("[4/6] Evaluating Tier 2 (1000–1200 Elo: Agro Hybrid with Strawberry Transition)...");
    let t2 = run_tier_eval(AgroHybridPolicy::new, "Tier 2: Agro Hybrids", "1000–1200", &tier_seeds);

    println!("[5/6] Evaluating Tier 3 (1200–1400 Elo: D.1 Grandmaster)...");
    let t3 = run_tier_eval(D1Policy::new, "Tier 3: GM Prototypes", "1200–1400", &tier_seeds);

    println!("[6/6] Evaluating Tier 4 (1400–1800+ Elo: Adaptive Terminal)...");
    let t4 = run_tier_eval(AdaptiveTerminalPolicy::new, "Tier 4: Adaptive Peak", "1400–1800+", &tier_seeds);

    let elapsed = t0.elapsed().as_secs_f64();
    println!("\nAll Tournaments Completed in {:.2}s ({:.1} matches/sec)\n", elapsed, (total_h2h + 16000) as f64 / elapsed);

    println!("=========================================================================================================================");
    println!("                                   EXP198 MULTI-TIER SCORECARD                                                           ");
    println!("=========================================================================================================================");
    println!("{:<24} | {:<10} | {:<24} | {:<12} | {:<12} | {:<12} | {:<12}",
        "Tier & Opponent", "Elo Band", "Win / Tie / Loss", "Hero Mean", "Opp Mean", "Net Delta", "Worst 5% Floor");
    println!("-------------------------------------------------------------------------------------------------------------------------");

    for t in &[&t1, &t2, &t3, &t4] {
        let wr = (t.hero_wins as f64 / t.total as f64) * 100.0;
        let tr = (t.ties as f64 / t.total as f64) * 100.0;
        let lr = (t.opp_wins as f64 / t.total as f64) * 100.0;
        let delta = t.hero_mean - t.opp_mean;

        println!("{:<24} | {:<10} | {:>4.1}% / {:>3.1}% / {:>4.1}% | ${:<11.1} | ${:<11.1} | {:>+11.1} | ${:<11.1}",
            t.name, t.elo_range, wr, tr, lr, t.hero_mean, t.opp_mean, delta, t.hero_worst_5pct);
    }
    println!("=========================================================================================================================");
}

pub mod engine;
pub mod farm;
pub mod workers;
pub mod market;
pub mod rng;
pub mod policies;
pub mod replay;
pub mod batch;

use policies::{Policy, PassPolicy, StarterCarrotPolicy, V41Policy, D1Policy, AdaptiveTerminalPolicy};
use std::fs::File;
use std::io::Write;
use std::time::Instant;

fn resolve_policy(name: &str) -> Box<dyn Policy> {
    match name {
        "pass" => Box::new(PassPolicy),
        "starter" => Box::new(StarterCarrotPolicy),
        "v41" | "v41_historical" => Box::new(V41Policy::new()),
        "d1" | "d1_control" => Box::new(D1Policy::new()),
        "adaptive" | "adaptive_terminal" => Box::new(AdaptiveTerminalPolicy::new()),
        _ => Box::new(PassPolicy),
    }
}

fn print_help() {
    println!("FastSim: High-Fidelity Research Engine for Kaggriculture");
    println!("Usage: fastsim [OPTIONS]");
    println!("Options:");
    println!("  --seed <SEED>           Episode random seed (default: 0)");
    println!("  --seat <0|1>            Hero seat index (default: 0)");
    println!("  --hero <NAME>           Hero policy name: starter, pass (default: starter)");
    println!("  --opponent <NAME>       Opponent policy name: starter, pass (default: pass)");
    println!("  --output <PATH>         Export normalized checkpoint trace JSON");
    println!("  --benchmark <N>         Run multi-threaded batch benchmark across N episodes");
    println!("  --help                  Show this help message");
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut seed: u64 = 0;
    let mut seat: usize = 0;
    let mut hero = "starter".to_string();
    let mut opponent = "pass".to_string();
    let mut output: Option<String> = None;
    let mut benchmark: Option<usize> = None;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--seed" | "-s" => {
                if i + 1 < args.len() { seed = args[i + 1].parse().unwrap_or(0); i += 1; }
            }
            "--seat" => {
                if i + 1 < args.len() { seat = args[i + 1].parse().unwrap_or(0); i += 1; }
            }
            "--hero" => {
                if i + 1 < args.len() { hero = args[i + 1].clone(); i += 1; }
            }
            "--opponent" => {
                if i + 1 < args.len() { opponent = args[i + 1].clone(); i += 1; }
            }
            "--output" | "-o" => {
                if i + 1 < args.len() { output = Some(args[i + 1].clone()); i += 1; }
            }
            "--benchmark" => {
                if i + 1 < args.len() { benchmark = args[i + 1].parse().ok(); i += 1; }
            }
            "--help" | "-h" => {
                print_help();
                return;
            }
            _ => {}
        }
        i += 1;
    }

    let hero_policy = resolve_policy(&hero);
    let opp_policy = resolve_policy(&opponent);

    if let Some(num_episodes) = benchmark {
        println!("Running FastSim benchmark on {} episodes (multi-threaded CPU)...", num_episodes);
        let seeds: Vec<u64> = (1..=(num_episodes as u64 / 2).max(1)).collect();
        let t0 = Instant::now();
        let traces = batch::run_batch(&seeds, &*hero_policy, &*opp_policy);
        let elapsed = t0.elapsed().as_secs_f64();
        let total_matches = traces.len();
        let rate = total_matches as f64 / elapsed;
        println!("Completed {} episodes in {:.3}s ({:.1} episodes/sec)!", total_matches, elapsed, rate);
        return;
    }

    let trace = batch::run_episode(seed, seat, &*hero_policy, &*opp_policy);

    println!(
        "Episode Finished | Seed: {} | Seat: {} | Hero ({}): ${:.0} vs Opp ({}): ${:.0} | Won: {}",
        seed,
        seat,
        hero,
        trace.final_rewards[seat],
        opponent,
        trace.final_rewards[1 - seat],
        trace.hero_won
    );

    if let Some(out_path) = output {
        let json_str = serde_json::to_string_pretty(&trace).expect("Failed to serialize trace");
        let mut file = File::create(&out_path).expect("Failed to create output trace file");
        file.write_all(json_str.as_bytes()).expect("Failed to write trace");
        println!("Saved normalized JSON trace to: {}", out_path);
    }
}

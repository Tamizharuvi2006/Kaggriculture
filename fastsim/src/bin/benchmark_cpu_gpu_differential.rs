//! EXP200.5 — CPU vs GPU Differential Correctness & Throughput Benchmark.
//! Compares native Rust CPU Q-inference against PyTorch GPU Batch Engine across 100, 1,000, and 10,000 states.

use fastsim::engine::state::GameState;
use fastsim::policies::exp200_competitive_policy::{EXP200CompetitivePolicy, CompetitiveQWeights};
use rayon::prelude::*;
use std::fs::File;
use std::io::Write;
use std::time::Instant;

fn main() {
    println!("=========================================================================================");
    println!("     EXP200.5 — CPU VS GPU DIFFERENTIAL CORRECTNESS & THROUGHPUT BENCHMARK              ");
    println!("=========================================================================================");

    let policy = EXP200CompetitivePolicy::new();
    let n_states = 10000;
    let seeds: Vec<u64> = (300000..300000 + n_states as u64).collect();

    println!("Extracting {} realistic decision states from game engine...", n_states);
    let mut states_vec = Vec::with_capacity(n_states);
    for &seed in &seeds {
        let st = GameState::new(seed, 10, 3000.0, 720, 24, 100);
        let feat = EXP200CompetitivePolicy::extract_features(&st, 0);
        states_vec.push(feat);
    }

    // 1. Benchmark Sequential Rust CPU Inference
    let t_seq_0 = Instant::now();
    let mut cpu_seq_preds = Vec::with_capacity(n_states);
    for feat in &states_vec {
        let q_scores = policy.forward(feat);
        cpu_seq_preds.push(q_scores);
    }
    let t_seq = t_seq_0.elapsed().as_secs_f64();
    let cpu_seq_throughput = n_states as f64 / t_seq;

    // 2. Benchmark Parallel Rayon Rust CPU Inference
    let t_par_0 = Instant::now();
    let cpu_par_preds: Vec<[f32; 6]> = states_vec.par_iter().map(|feat| {
        policy.forward(feat)
    }).collect();
    let t_par = t_par_0.elapsed().as_secs_f64();
    let cpu_par_throughput = n_states as f64 / t_par;

    println!("-----------------------------------------------------------------------------------------");
    println!("Rust CPU Sequential Inference Throughput : {:>10.0} inferences/sec ({:.2} ms / 10k states)",
        cpu_seq_throughput, t_seq * 1000.0);
    println!("Rust CPU Parallel (12 threads) Throughput: {:>10.0} inferences/sec ({:.2} ms / 10k states)",
        cpu_par_throughput, t_par * 1000.0);

    // Save states to CSV for Python GPU validation
    let csv_path = r"D:\kaggriculture\data\exp200_5_states_for_diff_test.csv";
    let mut file = File::create(csv_path).expect("Failed to create CSV");
    writeln!(file, "f0,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,q0,q1,q2,q3,q4,q5").unwrap();
    for i in 0..n_states {
        let f = states_vec[i];
        let q = cpu_seq_preds[i];
        writeln!(file, "{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}",
            f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7], f[8], f[9], f[10], f[11], f[12], f[13], f[14], f[15],
            q[0], q[1], q[2], q[3], q[4], q[5]).unwrap();
    }
    println!("Saved {} states and CPU reference Q-values to {}", n_states, csv_path);
    println!("=========================================================================================");
}

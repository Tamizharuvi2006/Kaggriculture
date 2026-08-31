use fastsim::policies::{D1Policy, AdaptiveTerminalPolicy, V41Policy};
use fastsim::batch::run_batch;
use std::time::Instant;

fn main() {
    println!("================================================================================");
    println!("FASTSIM 10,000-EPISODE MEGA-TOURNAMENT: ADAPTIVE vs D1 CONTROL");
    println!("================================================================================");

    let d1 = D1Policy::new();
    let adaptive = AdaptiveTerminalPolicy::new();

    let seeds: Vec<u64> = (1000..6000).collect(); // 5,000 seeds x 2 seats = 10,000 matches

    let t0 = Instant::now();
    let traces = run_batch(&seeds, &adaptive, &d1);
    let elapsed = t0.elapsed().as_secs_f64();

    let total = traces.len();
    let mut adaptive_wins = 0;
    let mut d1_wins = 0;
    let mut ties = 0;

    let mut adaptive_rewards = Vec::with_capacity(total);
    let mut d1_rewards = Vec::with_capacity(total);

    for trace in &traces {
        let seat = trace.hero_seat;
        let r_adaptive = trace.final_rewards[seat];
        let r_d1 = trace.final_rewards[1 - seat];

        adaptive_rewards.push(r_adaptive);
        d1_rewards.push(r_d1);

        if r_adaptive > r_d1 + 1.0 {
            adaptive_wins += 1;
        } else if r_d1 > r_adaptive + 1.0 {
            d1_wins += 1;
        } else {
            ties += 1;
        }
    }

    let mean_adaptive: f64 = adaptive_rewards.iter().sum::<f64>() / total as f64;
    let mean_d1: f64 = d1_rewards.iter().sum::<f64>() / total as f64;
    let win_rate = (adaptive_wins as f64 / total as f64) * 100.0;

    println!("Total Matches : {}", total);
    println!("Time Elapsed  : {:.3}s ({:.1} matches/sec)", elapsed, total as f64 / elapsed);
    println!("Adaptive Wins : {} ({:.2}%)", adaptive_wins, win_rate);
    println!("D1 Wins       : {} ({:.2}%)", d1_wins, (d1_wins as f64 / total as f64) * 100.0);
    println!("Ties          : {} ({:.2}%)", ties, (ties as f64 / total as f64) * 100.0);
    println!("Adaptive Mean : ${:.2}", mean_adaptive);
    println!("D1 Mean       : ${:.2}", mean_d1);
    println!("Delta Margin  : +${:.2}", mean_adaptive - mean_d1);
    println!("================================================================================");
}

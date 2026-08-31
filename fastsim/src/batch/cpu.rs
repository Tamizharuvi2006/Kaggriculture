use crate::engine::state::GameState;
use crate::engine::step::step_game;
use crate::policies::Policy;
use crate::replay::trace::{EpisodeTrace, CHECKPOINT_STEPS};
use rayon::prelude::*;

pub fn run_episode(
    seed: u64,
    hero_seat: usize,
    hero_policy: &dyn Policy,
    opp_policy: &dyn Policy,
) -> EpisodeTrace {
    let mut state = GameState::new(seed, 10, 3000.0, 720, 24, 100);
    let mut trace = EpisodeTrace::new(seed, hero_seat, hero_policy.name(), opp_policy.name());

    let opp_seat = 1 - hero_seat;
    let checkpoints_set: std::collections::HashSet<usize> = CHECKPOINT_STEPS.iter().cloned().collect();

    while !state.done && state.step < 720 {
        if checkpoints_set.contains(&state.step) {
            trace.record_checkpoint(&state, hero_seat);
        }

        let a_hero = hero_policy.act(&state, hero_seat);
        let a_opp = opp_policy.act(&state, opp_seat);

        let actions = if hero_seat == 0 {
            [a_hero, a_opp]
        } else {
            [a_opp, a_hero]
        };

        step_game(&mut state, &actions);
    }

    if checkpoints_set.contains(&720) || state.done {
        trace.record_checkpoint(&state, hero_seat);
    }

    trace.final_rewards = [state.farms[0].money, state.farms[1].money];
    trace.hero_won = state.farms[hero_seat].money > state.farms[opp_seat].money;

    trace
}

pub fn run_batch(
    seeds: &[u64],
    hero_policy: &(dyn Policy + Sync),
    opp_policy: &(dyn Policy + Sync),
) -> Vec<EpisodeTrace> {
    let mut tasks = Vec::new();
    for &seed in seeds {
        tasks.push((seed, 0));
        tasks.push((seed, 1));
    }

    tasks.into_par_iter().map(|(seed, seat)| {
        run_episode(seed, seat, hero_policy, opp_policy)
    }).collect()
}

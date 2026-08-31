pub mod scripted;
pub mod v41;
pub mod d1;
pub mod adaptive;
pub mod multicrop_planner;
pub mod neural_bc_policy;
pub mod hierarchical_bc_policy;
pub mod target_dispatcher;
pub mod q_guided_dispatcher;
pub mod model_based_rollout;
pub mod residual_q_adaptive;
pub mod exp185_verified_policy;
pub mod exp185_1_sparse_gated;
pub mod exp186_rescue_policy;
pub mod adaptive_guarded;
pub mod adaptive_sized;
pub mod exp191_decision_policy;
pub mod exp192_verified_sheep_policy;
pub mod agro_hybrid;
pub mod exp193_macro_policy;
pub mod exp194_opponent_policy;
pub mod exp195_temporal_policy;
pub mod exp196_trinary_policy;
pub mod exp197_contrastive_policy;
pub mod exp198_alpha_policy;

use crate::engine::state::GameState;
use crate::engine::step::PlayerAction;

pub trait Policy: Send + Sync {
    fn name(&self) -> &'static str;
    fn act(&self, state: &GameState, player_idx: usize) -> PlayerAction;
}

pub use scripted::{PassPolicy, StarterCarrotPolicy};
pub use v41::V41Policy;
pub use d1::D1Policy;
pub use adaptive::AdaptiveTerminalPolicy;
pub use multicrop_planner::MultiCropPlannerPolicy;
pub use neural_bc_policy::NeuralBCPolicy;
pub use hierarchical_bc_policy::HierarchicalBCPolicy;
pub use target_dispatcher::TargetDispatcherPolicy;
pub use q_guided_dispatcher::QGuidedDispatcherPolicy;
pub use model_based_rollout::ModelBasedRolloutPolicy;
pub use residual_q_adaptive::ResidualQAdaptivePolicy;
pub use exp185_verified_policy::EXP185VerifiedPolicy;
pub use exp185_1_sparse_gated::{EXP185_1_SparseGatedPolicy, SparseGatedConfig};
pub use exp186_rescue_policy::EXP186RescuePolicy;
pub use adaptive_guarded::AdaptiveGuardedPolicy;
pub use adaptive_sized::AdaptiveSizedPolicy;
pub use exp191_decision_policy::AdaptiveDecisionPolicy;
pub use exp192_verified_sheep_policy::EXP192VerifiedSheepPolicy;
pub use agro_hybrid::AgroHybridPolicy;
pub use exp193_macro_policy::EXP193MacroPolicy;
pub use exp194_opponent_policy::EXP194OpponentPolicy;
pub use exp195_temporal_policy::EXP195TemporalPolicy;
pub use exp196_trinary_policy::EXP196TrinaryPolicy;
pub use exp197_contrastive_policy::EXP197ContrastivePolicy;
pub use exp198_alpha_policy::EXP198AlphaPolicy;
pub mod exp200_competitive_policy;
pub use exp200_competitive_policy::EXP200CompetitivePolicy;
pub mod exp202_elite_blueprint;
pub use exp202_elite_blueprint::EXP202EliteBlueprintPolicy;
pub mod exp203_regime_policy;
pub use exp203_regime_policy::EXP203RegimePolicy;
pub mod exp204_elite_bc_policy;
pub use exp204_elite_bc_policy::EXP204EliteBCPolicy;
pub mod exp205_frontier_policy;
pub use exp205_frontier_policy::EXP205FrontierPolicy;
pub mod elite_opponents;
pub use elite_opponents::{
    Elite1800_2200Policy, Elite2200_2600Policy, Elite2600_3000Policy,
    Elite3000OpponentA, Elite3000OpponentB, Elite3000OpponentC, Elite3000OpponentD
};
pub mod exp208_champion_policy;
pub use exp208_champion_policy::EXP208ChampionPolicy;
pub mod unseen_elite_opponents;
pub use unseen_elite_opponents::{
    UnseenElite1800_2200, UnseenElite2200_2600, UnseenElite2600_3000,
    UnseenElite3000_BotE, UnseenElite3000_BotF
};
pub mod adversarial_opponents;
pub use adversarial_opponents::{
    AdversarialHardMirror, AdversarialAgroLivestock, AdversarialApexGrandmaster, AdversarialMarketPredator
};



























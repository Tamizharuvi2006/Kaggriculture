"""
1. Telemetry Ingestor (Read-Only)
Ingests live Kaggle match logs, parses outcomes, action distributions, PASS events,
pricing trajectories, and player economy states without modifying production.

Supports BOTH real formats:
  - reports/live_match_telemetry/submission_*.json (Kaggle episodes API format)
  - generic per-step replay rows (mcv_replay_dataset.json schema)
"""
import os
import json
import glob
from typing import Dict, Any, List, Optional


class TelemetryIngestor:
    def __init__(self, logs_dir: str = "reports/live_match_telemetry"):
        self.logs_dir = logs_dir

    def parse_match_log(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Parses a single match JSON/log file and extracts key match telemetry."""
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return {"error": f"Failed to parse JSON: {e}", "filepath": filepath}

        # Extract normalized telemetry schema
        match_id = data.get("match_id") or data.get("episode_id") or os.path.basename(filepath)
        result = data.get("result", "UNKNOWN")
        our_mcv = data.get("our_mcv", data.get("final_wealth", 0))
        opp_mcv = data.get("opp_mcv", data.get("opponent_wealth", 0))
        pass_turns = data.get("pass_turns", data.get("idle_turns", 0))
        total_steps = data.get("total_steps", 360)
        seat = data.get("seat", data.get("player_index", 0))

        telemetry = {
            "match_id": str(match_id),
            "filepath": filepath,
            "result": "WIN" if our_mcv > opp_mcv else ("LOSS" if our_mcv < opp_mcv else "TIE"),
            "our_mcv": our_mcv,
            "opp_mcv": opp_mcv,
            "mcv_diff": our_mcv - opp_mcv,
            "seat": seat,
            "pass_turns": pass_turns,
            "pass_ratio": pass_turns / max(1, total_steps),
            "total_steps": total_steps,
            "actions_summary": data.get("actions_summary", {}),
            "market_events": data.get("market_events", []),
            "raw_metadata": {k: v for k, v in data.items() if k not in ["steps", "states"]}
        }
        return telemetry

    def parse_kaggle_episodes(self, filepath: str, our_submission_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Parses the REAL Kaggle episode export format:
        {submission: {ref, publicScore, ...}, episodes: [{id, state, agents: [
            {submissionId, reward, index, initialScore, updatedScore}]}]}

        our_submission_id defaults to the file's own submission ref, so each
        submission's episode file yields that submission's matches.
        """
        if not os.path.exists(filepath):
            return []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []

        if our_submission_id is None:
            our_submission_id = data.get("submission", {}).get("ref")

        telemetry_list = []
        for episode in data.get("episodes", []):
            if episode.get("state") != "COMPLETED":
                continue

            agents = episode.get("agents", [])
            our_agent = next((a for a in agents if a.get("submissionId") == our_submission_id), None)
            if our_agent is None:
                continue
            opponent = next((a for a in agents if a.get("submissionId") != our_submission_id), None)
            if opponent is None:
                continue

            our_mcv = our_agent.get("reward", 0)
            opp_mcv = opponent.get("reward", 0)
            seat = our_agent.get("index", 0)

            telemetry_list.append({
                "match_id": str(episode.get("id")),
                "filepath": filepath,
                "result": "WIN" if our_mcv > opp_mcv else ("LOSS" if our_mcv < opp_mcv else "TIE"),
                "our_mcv": our_mcv,
                "opp_mcv": opp_mcv,
                "mcv_diff": our_mcv - opp_mcv,
                "seat": seat,
                "our_elo_delta": round(our_agent.get("updatedScore", 0) - our_agent.get("initialScore", 0), 4),
                "opponent_submission_id": opponent.get("submissionId"),
                "pass_turns": 0,
                "pass_ratio": 0.0,
                "total_steps": 360,
                "actions_summary": {},
                "market_events": [],
                "raw_metadata": {"episode_id": episode.get("id"),
                                 "create_time": episode.get("createTime"),
                                 "end_time": episode.get("endTime"),
                                 "type": episode.get("type"),
                                 "our_agent_id": our_agent.get("id")}
            })
        return telemetry_list

    def ingest_recent_matches(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scans logs directory for recent match files and ingests them."""
        if not os.path.exists(self.logs_dir):
            return []

        pattern = os.path.join(self.logs_dir, "*.json")
        files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        results = []
        for f in files[:limit]:
            parsed = self.parse_match_log(f)
            if parsed and "error" not in parsed:
                results.append(parsed)
        return results

    def ingest_live_telemetry(self, telemetry_dir: str = None) -> List[Dict[str, Any]]:
        """
        Ingests every real Kaggle episode export under reports/live_match_telemetry
        (submission_*.json), attributing each match to the file's own submission.
        """
        directory = telemetry_dir or self.logs_dir
        if not os.path.exists(directory):
            return []

        results = []
        for f in sorted(glob.glob(os.path.join(directory, "submission_*_episodes.json"))):
            results.extend(self.parse_kaggle_episodes(f))
        return results


if __name__ == "__main__":
    ingestor = TelemetryIngestor()
    live = ingestor.ingest_live_telemetry()
    wins = sum(1 for m in live if m["result"] == "WIN")
    print(f"Telemetry Ingestor initialized. Watching {ingestor.logs_dir}/")
    print(f"Real live matches ingested: {len(live)} (Wins: {wins}, Losses: {len(live) - wins})")

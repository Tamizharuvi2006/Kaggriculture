"""
APEX 4.0 Closed-Loop Master Controller
"""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apex_next.apex4.world_model.world_model import APEX4WorldModel
from apex_next.apex4.task_graph.task_graph import APEX4TaskGraph
from apex_next.apex4.opponent_model.opponent_tracker import OpponentTracker


class APEX4Controller:
    """
    Master closed-loop decision engine for APEX 4.0.
    """
    def __init__(self):
        self.world_model = APEX4WorldModel()
        self.task_graph = APEX4TaskGraph()
        self.opp_tracker = OpponentTracker()

    def plan_step(self, obs, fallback_action=None):
        self.world_model.update(obs)
        self.opp_tracker.update(self.world_model)
        tasks = self.task_graph.evaluate_tasks(self.world_model)
        
        step = self.world_model.step
        hour = self.world_model.hour
        money = self.world_model.money
        unlocked = self.world_model.unlocked_quadrants
        shed = self.world_model.inventory
        
        market_orders = []
        hands_actions = []
        fb_hands = fallback_action.get("hands", []) if fallback_action else []
        fb_mkt = fallback_action.get("market", []) if fallback_action else []
        
        # -------------------------------------------------------------
        # 1. CLOSED-LOOP MARKET & RESOURCE SYNCHRONIZATION
        # -------------------------------------------------------------
        # Day 4 Melon Liquidity -> Strawberry Conversion
        if step == 75:
            melon_cnt = int(shed.get("MELON", 0) or 0)
            if melon_cnt >= 6:
                market_orders.append(["SELL", "MELON", melon_cnt])
                market_orders.append(["BUY_SEED", "STRAWBERRY", 6])

        # Step 152 Dynamic Land 2 Expansion
        if step == 152 and len(unlocked) == 1 and money >= 1000.0:
            market_orders.append(["BUY_LAND"])

        # Step 156 Synchronized Seed Purchase (Purchases 2 extra seeds for Worker #3)
        if step == 156:
            market_orders.append(["BUY_SEED", "STRAWBERRY", 2])

        # Hour 23 Clearance Selling
        if hour == 23 and step >= 200:
            straw_cnt = int(shed.get("STRAWBERRY", 0) or 0)
            milk_cnt = int(shed.get("MILK", 0) or 0)
            if straw_cnt >= 4:
                market_orders.append(["SELL", "STRAWBERRY", straw_cnt])
            if milk_cnt >= 4:
                market_orders.append(["SELL", "MILK", milk_cnt])

        # Terminal Feed Conservation (Steps 672+)
        is_terminal_feed_halt = False
        if step >= 672:
            shed_wheat = int(shed.get("WHEAT", 0) or 0)
            if shed_wheat >= 12:
                is_terminal_feed_halt = True

        # -------------------------------------------------------------
        # 2. CLOSED-LOOP WORKER ALLOCATION WITH PROTECTED MILESTONES
        # -------------------------------------------------------------
        # INVARIANT: Step 159 Pasture 2 Build by Workers #2 & #3 is 100% UNTOUCHED!
        # INVARIANT: Step 170 Cow Pickup by Worker #0 is 100% UNTOUCHED!
        for w_idx, w in enumerate(self.world_model.workers):
            # Worker #3 Post-Pasture Cultivation in Steps 160-167
            if w_idx == 3 and len(unlocked) >= 2 and 160 <= step <= 167:
                if step in (160, 161):
                    hands_actions.append(["SOUTH"])
                elif step == 162:
                    hands_actions.append(["TILL"])
                elif step == 163:
                    hands_actions.append(["PLANT", "STRAWBERRY"])
                elif step == 164:
                    hands_actions.append(["WATER"])
                elif step in (165, 166):
                    hands_actions.append(["NORTH"])
                elif step == 167:
                    hands_actions.append(["PASS"])
                continue

            # Routine / Fallback Worker Execution
            if fb_hands and len(fb_hands) > w_idx:
                hands_actions.append(fb_hands[w_idx])
            else:
                hands_actions.append(["PASS"])

        # Merge Market Orders
        final_market = []
        if fallback_action:
            for m in fb_mkt:
                if is_terminal_feed_halt and isinstance(m, list) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT":
                    continue
                final_market.append(m)
        for mo in market_orders:
            if mo not in final_market:
                final_market.append(mo)

        farmer_act = fallback_action.get("farmer", ["PASS"]) if fallback_action else ["PASS"]
        return {
            "farmer": farmer_act,
            "hands": hands_actions,
            "market": final_market[:10]
        }

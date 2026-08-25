"""
APEX 4.0 Master Persistent Regional Closed-Loop Controller
Implements continuous multi-cycle agricultural maintenance in newly unlocked quadrants.
"""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apex_next.apex4.world_model.world_model import APEX4WorldModel
from apex_next.apex4.region_manager.region_manager import RegionManager, RegionState
from apex_next.apex4.opponent_model.opponent_tracker import OpponentTracker


class APEX4RegionalController:
    """
    Closed-loop regional controller providing continuous farming in Region 2 (SW).
    """
    def __init__(self):
        self.world_model = APEX4WorldModel()
        self.region_manager = RegionManager()
        self.opp_tracker = OpponentTracker()
        
        # Assign persistent lease for Worker #4 to Region 2 (SW) from Step 172 to Step 719
        self.region_manager.assign_worker_lease(worker_idx=4, region_id=2, start_step=172, duration=548)

    def plan_step(self, obs, fallback_action=None):
        self.world_model.update(obs)
        self.region_manager.update(self.world_model)
        self.opp_tracker.update(self.world_model)
        
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
        # 1. CONTINUOUS RESOURCE & MARKET SYNCHRONIZATION
        # -------------------------------------------------------------
        # Step 75: Melon Liquidity Conversion
        if step == 75:
            melon_cnt = int(shed.get("MELON", 0) or 0)
            if melon_cnt >= 6:
                market_orders.append(["SELL", "MELON", melon_cnt])
                market_orders.append(["BUY_SEED", "STRAWBERRY", 6])

        # Step 152: Dynamic Land 2 Expansion
        if step == 152 and len(unlocked) == 1 and money >= 1000.0:
            market_orders.append(["BUY_LAND"])

        # Step 156: Synchronized Initial Seed Purchase for Worker #3
        if step == 156:
            market_orders.append(["BUY_SEED", "STRAWBERRY", 2])

        # Continuous SW Seed Replenishment (Buy 2 seeds every 48 steps after Step 200)
        if step >= 200 and (step % 48 == 0) and len(unlocked) >= 2 and money >= 300.0:
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
        # 2. PERSISTENT WORKER REGIONAL ALLOCATION
        # -------------------------------------------------------------
        for w_idx, w in enumerate(self.world_model.workers):
            # Worker #3 Initial Cultivation (Steps 160 to 167)
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

            # Worker #4 Persistent Regional Service in SW Quadrant (Steps 172 to 719)
            if w_idx == 4 and len(unlocked) >= 2 and step >= 172:
                cycle_step = (step - 172) % 48
                # Steps 0..3: Move to SW tile (7, 3)
                if cycle_step in (0, 1, 2, 3):
                    hands_actions.append(["SOUTH"])
                # Step 4: HARVEST ripe strawberry
                elif cycle_step == 4:
                    hands_actions.append(["HARVEST"])
                # Step 5: TILL soil
                elif cycle_step == 5:
                    hands_actions.append(["TILL"])
                # Step 6: REPLANT strawberry seed
                elif cycle_step == 6:
                    hands_actions.append(["PLANT", "STRAWBERRY"])
                # Step 7: WATER strawberry
                elif cycle_step == 7:
                    hands_actions.append(["WATER"])
                # Step 8..15: Periodic watering maintenance
                elif cycle_step in (16, 24, 32):
                    hands_actions.append(["WATER"])
                # Step 44..47: Move to shed to DROP inventory before Hour 23 clearance
                elif cycle_step in (44, 45):
                    hands_actions.append(["NORTH"])
                elif cycle_step == 46:
                    hands_actions.append(["DROP"])
                else:
                    hands_actions.append(["PASS"])
                continue

            # Routine / Fallback Worker Execution for Workers 0, 1, 2, 3, 5, 6, 7
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

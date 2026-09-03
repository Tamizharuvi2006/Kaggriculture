def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _copy_action(action):
    """Copy a scheduled action before an observation-dependent overlay."""
    if not isinstance(action, dict):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order) for order in (action.get("hands") or [])],
        "market": [list(order) for order in (action.get("market") or [])],
    }


def _v17_number(value, default=0.0):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _v18_state_features(obs):
    """Public own-state vector used by the offline and submission gates."""
    player = 1 if int(_get(obs, "player", 0) or 0) == 1 else 0
    farms = _get(obs, "farms", []) or []
    farm = farms[player] if player < len(farms) and isinstance(farms[player], dict) else {}
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", _get(market, "current_prices", {})) or {}
    counts = {
        name: 0.0
        for name in (
            "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "COW", "SHEEP", "GOOSE",
        )
    }
    for row in farm.get("tiles", []) or []:
        for tile in row if isinstance(row, list) else [row]:
            if not isinstance(tile, dict):
                continue
            crop = str(tile.get("crop", "")).upper()
            animal = str(tile.get("animal", tile.get("kind", ""))).upper()
            if crop in counts:
                counts[crop] += 1.0
            if animal in counts:
                counts[animal] += 1.0
    values = [
        math.log1p(max(0.0, _v17_number(farm.get("money", 0)))),
        len(farm.get("hands", []) or []) / 16.0,
        len(farm.get("unlocked_quadrants", []) or []) / 4.0,
    ]
    values.extend(
        counts[name] / 50.0
        for name in (
            "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "COW", "SHEEP", "GOOSE",
        )
    )
    values.extend(
        math.log1p(max(0.0, _v17_number(shed.get(name, 0))))
        for name in _V18_PRODUCTS
    )
    price_values = [
        max(1.0, _v17_number(prices.get(name, 1), 1.0))
        for name in _V18_PRODUCTS
    ]
    mean_price = sum(price_values) / len(price_values)
    values.extend(math.log(value / mean_price) for value in price_values)
    return values


def _v18_closed_loop_action(obs, step):
    """Lock a seat route and choose a complete market expert once per day.

    The learned choice is outcome-based: complete-game wins set the seat
    priors, and public state similarity supplies the closed-loop correction.
    No SELL-order imitation label is used at training or runtime.
    """
    global _V18_SELECTED_MARKET, _V18_SELECTED_DAY, _V18_SELECTED_BOARD
    seat = 1 if int(_get(obs, "player", 0) or 0) == 1 else 0
    experts = _V18_RUNTIME["experts"]
    base_board_name = _V18_RUNTIME["board_by_seat"][str(seat)]
    base_board_actions = experts[base_board_name]["actions"]
    bounded_step = min(max(0, int(step)), len(base_board_actions) - 1)
    if bounded_step == 0:
        _V18_SELECTED_MARKET[seat] = None
        _V18_SELECTED_DAY[seat] = None
        _V18_SELECTED_BOARD[seat] = None

    board_strength = float(_V18_RUNTIME.get("board_distance_strength", 0.0))
    board_fork_step = int(_V18_RUNTIME.get("board_fork_step", len(base_board_actions)))
    if (
        STRATEGY.get("v18_closed_loop_board", True)
        and board_strength > 0.0
        and bounded_step >= board_fork_step
        and _V18_SELECTED_BOARD[seat] is None
    ):
        current = _v18_state_features(obs)
        scales = _V18_RUNTIME["feature_standardization"]["scale"]
        bias = _V18_RUNTIME["board_bias_by_seat"][str(seat)]
        best_board = None
        for name, expert in experts.items():
            prototype = expert["board_prototype_at_fork"]
            distance = sum(
                ((value - center) / max(1e-12, float(scale))) ** 2
                for value, center, scale in zip(current, prototype, scales)
            ) / len(current)
            candidate = (float(bias.get(name, 0.0)) - board_strength * distance, name)
            if best_board is None or candidate > best_board:
                best_board = candidate
        _V18_SELECTED_BOARD[seat] = best_board[1]

    board_name = _V18_SELECTED_BOARD[seat] or base_board_name
    board_actions = experts[board_name]["actions"]
    board_action = board_actions[bounded_step] or {
        "farmer": ["PASS"], "hands": [], "market": [],
    }
    if not STRATEGY.get("v18_closed_loop_market", True):
        return _copy_action(board_action)

    day = max(0, int(_get(obs, "day", bounded_step // 24) or 0))
    if _V18_SELECTED_DAY[seat] != day or _V18_SELECTED_MARKET[seat] is None:
        current = _v18_state_features(obs)
        scales = _V18_RUNTIME["feature_standardization"]["scale"]
        bias = _V18_RUNTIME["market_bias_by_seat"][str(seat)]
        distance_strength = float(_V18_RUNTIME["distance_strength"])
        stay_bonus = float(_V18_RUNTIME["stay_bonus"])
        selected = _V18_SELECTED_MARKET[seat]
        best = None
        for name, expert in experts.items():
            prototypes = expert["prototypes_by_day"]
            prototype = prototypes[min(day, len(prototypes) - 1)]
            distance = sum(
                ((value - center) / max(1e-12, float(scale))) ** 2
                for value, center, scale in zip(current, prototype, scales)
            ) / len(current)
            score = float(bias.get(name, 0.0)) - distance_strength * distance
            if name == selected:
                score += stay_bonus
            candidate = (score, name)
            if best is None or candidate > best:
                best = candidate
        _V18_SELECTED_MARKET[seat] = best[1]
        _V18_SELECTED_DAY[seat] = day

    market_name = _V18_SELECTED_MARKET[seat]
    market_actions = experts[market_name]["actions"]
    market_action = market_actions[min(bounded_step, len(market_actions) - 1)] or {}
    return {
        "farmer": list(board_action.get("farmer") or ["PASS"]),
        "hands": [list(order) for order in (board_action.get("hands") or [])],
        "market": [list(order) for order in (market_action.get("market") or [])],
    }


def _public_farm_counts(farm):
    """Return stable public portfolio features for a farm.

    Fixed replay executors cannot safely swap movement trajectories halfway
    through a game.  Animal species and within-turn purchase priority are
    different: both share the same pasture sites and unit actions, so they can
    react to public state without invalidating the remaining executor.
    """
    counts = {
        "COW": 0,
        "SHEEP": 0,
        "GOOSE": 0,
        "PLANTS": 0,
        "STRAWBERRY": 0,
        "LAND": len(_get(farm, "unlocked_quadrants", []) or []),
        "MONEY": float(_get(farm, "money", 0) or 0),
    }
    for row in (_get(farm, "tiles", []) or []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            animal = tile.get("animal")
            if animal in ("COW", "SHEEP", "GOOSE"):
                counts[animal] += 1
            if tile.get("kind") == "PLANT":
                counts["PLANTS"] += 1
                if tile.get("crop") == "STRAWBERRY":
                    counts["STRAWBERRY"] += 1
    counts["ANIMALS"] = counts["COW"] + counts["SHEEP"] + counts["GOOSE"]
    return counts


def _prioritize_capital_orders(obs, orders, own, opponent):
    """Spend existing early orders sooner when the rival is accelerating.

    WHEAT orders keep their exact slots and relative order because the fixed
    executor uses them as a cash cycle.  Only non-WHEAT slots are permuted.
    """
    if not STRATEGY.get("adaptive_capital_priority"):
        return orders
    if int(_get(obs, "day", 0)) > int(STRATEGY.get("adaptive_capital_max_day", 12)):
        return orders
    animal_pressure = opponent["ANIMALS"] >= own["ANIMALS"] + int(
        STRATEGY.get("adaptive_capital_animal_lead", 2)
    )
    land_pressure = opponent["LAND"] >= own["LAND"] + int(
        STRATEGY.get("adaptive_capital_land_lead", 1)
    )
    if not (animal_pressure or land_pressure):
        return orders

    movable = []
    positions = []
    for index, order in enumerate(orders):
        if len(order) > 1 and order[1] == "WHEAT" and order[0] in {"BUY_PRODUCT", "SELL"}:
            continue
        positions.append(index)
        movable.append(order)

    def priority(pair):
        index, order = pair
        command = order[0] if order else ""
        if command == "SELL":
            return (0, index)
        if command in {"BUY_LAND", "BUY_ANIMAL"}:
            return (1, index)
        if command == "HIRE":
            return (2, index)
        return (3, index)

    reordered = list(orders)
    sorted_orders = [order for _, order in sorted(enumerate(movable), key=priority)]
    for index, order in zip(positions, sorted_orders):
        reordered[index] = order
    return reordered


def _adaptive_animal_focus(obs, own, opponent):
    """Choose a livestock market to contest from observable exposure only."""
    day = int(_get(obs, "day", 0))
    if not (
        int(STRATEGY.get("adaptive_animal_min_day", 2))
        <= day
        <= int(STRATEGY.get("adaptive_animal_max_day", 14))
    ):
        return None
    opponent_herd = opponent["COW"] + opponent["SHEEP"]
    if opponent_herd < int(STRATEGY.get("adaptive_animal_min_herd", 4)):
        return None
    lead = int(STRATEGY.get("adaptive_animal_lead", 2))
    if opponent["COW"] >= opponent["SHEEP"] + lead:
        focus = "COW"
    elif opponent["SHEEP"] >= opponent["COW"] + lead:
        focus = "SHEEP"
    elif STRATEGY.get("adaptive_tempo_cow") and (
        opponent["ANIMALS"] >= own["ANIMALS"] + int(
            STRATEGY.get("adaptive_tempo_animal_lead", 1)
        )
        or opponent["LAND"] >= own["LAND"] + int(
            STRATEGY.get("adaptive_tempo_land_lead", 1)
        )
    ):
        # Cows are the cheaper livestock asset and start the milk cycle sooner.
        # When a balanced rival is already ahead on capital, this is a recovery
        # branch rather than an attempt to infer a nonexistent specialization.
        focus = "COW"
    else:
        return None
    if STRATEGY.get("adaptive_animal_mode") == "diversify":
        focus = "SHEEP" if focus == "COW" else "COW"
    share = max(0.5, min(1.0, float(STRATEGY.get("adaptive_animal_target_share", 0.72))))
    own_herd = own["COW"] + own["SHEEP"]
    # Do not blindly convert every future purchase.  Stop contesting once the
    # requested share is already represented in our live herd.
    target = int(round((own_herd + 1) * share))
    return focus if own[focus] < target else None


def _apply_fixed_board_adaptation(obs, action):
    """Observation-only adaptation layered on a validated fixed executor."""
    copied = _copy_action(action)
    if not STRATEGY.get("fixed_board_adaptation"):
        return copied
    farms = _get(obs, "farms", []) or []
    player = int(_get(obs, "player", 0))
    if len(farms) != 2 or player not in (0, 1):
        return copied
    own = _public_farm_counts(farms[player])
    opponent = _public_farm_counts(farms[1 - player])
    focus = _adaptive_animal_focus(obs, own, opponent)
    if focus:
        for order in copied["market"]:
            if order and order[0] == "BUY_ANIMAL" and len(order) >= 2:
                order[1] = focus
    copied["market"] = _prioritize_capital_orders(obs, copied["market"], own, opponent)[:MAX_ORDERS]
    return copied


def _base_agent(obs):
    """Kaggle entry point."""
    try:
        if STRATEGY.get("use_fixed_schedule"):
            version = STRATEGY.get("fixed_schedule_version")
            player = int(_get(obs, "player", 0))
            use_radiant = version == "v11" and player == int(
                STRATEGY.get("v11_radiant_player", 0)
            )
            if use_radiant:
                step = min(max(0, int(_get(obs, "step", 0))), len(_V11_RADIANT_SCHEDULE) - 1)
                schedule = _v11_radiant_schedule(obs, step)
            elif version == "v18":
                board_name = _V18_RUNTIME["board_by_seat"][str(1 if player == 1 else 0)]
                schedule = _V18_RUNTIME["experts"][board_name]["actions"]
            elif version == "v17":
                schedule = _V17_SCHEDULE
            elif version == "v16":
                schedule = _v16_core_schedule(obs)
            elif version in {"v13", "v14", "v15"}:
                schedule = _V13_SENKIN_SCHEDULE
            elif version == "v12":
                schedule = _V12_SYOUYA_SCHEDULE
            elif version in {"v10", "v11"}:
                schedule = _V10_SCHEDULE
            else:
                schedule = _FIXED_SCHEDULE
            step = min(max(0, int(_get(obs, "step", 0))), len(schedule) - 1)
            action = schedule[step]
            raw = (
                _v15_senkin_action(obs, step)
                if version == "v15"
                else _v14_senkin_action(obs, step)
                if version == "v14"
                else _v13_senkin_action(obs, step)
                if version == "v13"
                else _v16_senkin_action(obs, step)
                if version == "v16"
                else _v18_closed_loop_action(obs, step)
                if version == "v18"
                else _v17_learned_action(obs, step)
                if version == "v17"
                else _v12_syouya_action(obs, step)
                if version == "v12"
                else action or {"farmer": ["PASS"], "hands": [], "market": []}
            )
            use_interference = (
                (version == "v12" and STRATEGY.get("v12_market_interference"))
                or (use_radiant and STRATEGY.get("v11_radiant_market_interference"))
                or (version not in {"v12", "v13", "v14", "v15", "v16", "v17", "v18"} and not use_radiant)
            )
            overlaid = (
                _apply_market_interference(obs, raw)
                if use_interference
                else _copy_action(raw)
            )
            return _apply_fixed_board_adaptation(obs, overlaid)
        _observe_opponent(obs)
        unit_actions = _assign_actions(obs)
        return {
            "farmer": unit_actions[0] if unit_actions else ["PASS"],
            "hands": unit_actions[1:],
            "market": _market_orders(obs),
        }
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}


def agent(obs, configuration=None):
    """Kaggle tournament submission entry point with EXP208 Champion Policy."""
    global _EXP208_PRICE_HISTORY
    try:
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        day = int(obs.get("day", step // 24) if isinstance(obs, dict) else getattr(obs, "day", step // 24) or 0)
        hour = int(obs.get("hour", step % 24) if isinstance(obs, dict) else getattr(obs, "hour", step % 24) or 0)

        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        own_farm = farms[player] if len(farms) > player else {}
        money = float(own_farm.get("money", 0.0) or 0.0)
        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}
        milk_in_shed = int(shed.get("MILK", 0) or 0)
        fert_in_shed = int(shed.get("FERTILIZER", 0) or 0)
        straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)
        wool_in_shed = int(shed.get("WOOL", 0) or 0)
        unlocked = own_farm.get("unlocked_quadrants") or ["NW"]
        hands = own_farm.get("hands") or []

        mkt = obs.get("market") or {} if isinstance(obs, dict) else getattr(obs, "market", {}) or {}
        prices = mkt.get("prices") or {}
        p_fert = float(prices.get("FERTILIZER", 80.0) or 80.0)
        p_wheat = float(prices.get("WHEAT", 30.0) or 30.0)
        p_milk = float(prices.get("MILK", 160.0) or 160.0)
        p_wool = float(prices.get("WOOL", 180.0) or 180.0)
        p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)

        act = _base_agent(obs)
        if not isinstance(act, dict):
            return act

        market_orders = list(act.get("market") or [])

        # 1. End of game clearance (step >= 690, Day 29+): Force sell everything
        if step >= 690:
            clean_orders = []
            if straw_in_shed > 0: clean_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
            if milk_in_shed > 0: clean_orders.append(["SELL", "MILK", milk_in_shed])
            if fert_in_shed > 0: clean_orders.append(["SELL", "FERTILIZER", fert_in_shed])
            if wool_in_shed > 0: clean_orders.append(["SELL", "WOOL", wool_in_shed])
            if clean_orders:
                act["market"] = clean_orders
            return act

        # 2. Continuous 3-Hour Fertilizer Micro-Liquidity Recycling
        if day >= 3 and hour % 3 == 0 and p_fert >= 48.0:
            if fert_in_shed >= 2 and not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "FERTILIZER" for m in market_orders):
                market_orders.append(["SELL", "FERTILIZER", fert_in_shed])

        # 3. Gated Elite Transitions:
        # Day 2: Early Wheat Feed + 1 Worker injection
        if day == 2 and hour == 2:
            if p_fert >= 48.0 and p_wheat <= 38.0 and money >= 150.0:
                if money >= 120.0 and not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT" for m in market_orders):
                    market_orders.append(["BUY_PRODUCT", "WHEAT", 4])
                if money >= 40.0 and len(hands) == 0 and not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "HIRE" for m in market_orders):
                    market_orders.append(["HIRE"])

        # Day 6: 4th Cow Reinvestment
        if day == 6 and hour == 16 and money >= 850.0 and p_milk >= 130.0:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "COW" for m in market_orders):
                market_orders.append(["BUY_ANIMAL", "COW", 1])

        # Day 7: Quadrant 2 Land Expansion
        if day == 7 and hour == 2 and money >= 500.0 and len(unlocked) < 2:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in market_orders):
                market_orders.append(["BUY_LAND"])

        # Day 8: Sized Sheep (Adaptive wool price cutoff)
        if day == 8 and hour == 4:
            market_orders = [m for m in market_orders if not (isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "SHEEP")]
            if p_wool >= 130.0 and money >= 2400.0:
                market_orders.append(["BUY_ANIMAL", "SHEEP", 4])
            elif money >= 1200.0:
                market_orders.append(["BUY_ANIMAL", "SHEEP", 2])
            elif money >= 600.0:
                market_orders.append(["BUY_ANIMAL", "SHEEP", 1])

        # Day 11-12: Quadrant 3 Early Land Expansion
        if (day == 11 or day == 12) and hour == 2 and money >= 810.0 and len(unlocked) == 2:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in market_orders):
                market_orders.append(["BUY_LAND"])

        # Enforce 3-quadrant maximum ceiling
        final_orders = []
        for m in market_orders:
            if isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND":
                if len(unlocked) >= 3:
                    continue
            final_orders.append(m)

        act["market"] = final_orders
        return act
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}



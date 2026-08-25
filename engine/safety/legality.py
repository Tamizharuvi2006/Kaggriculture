"""Legality validation for unit moves and market orders."""
from __future__ import annotations
from typing import List, Any, Dict, Tuple

class LegalityGuard:
    """Validates game engine legal constraints."""

    @staticmethod
    def filter_market_orders(orders: List[List[Any]], max_orders: int = 10) -> List[List[Any]]:
        valid = []
        for ord_item in orders:
            if not isinstance(ord_item, (list, tuple)) or not ord_item:
                continue
            op = ord_item[0]
            if op in ("HIRE", "BUY_LAND"):
                valid.append(list(ord_item))
            elif op in ("SELL", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL") and len(ord_item) >= 2:
                qty = int(ord_item[2]) if len(ord_item) >= 3 else 1
                if qty > 0:
                    valid.append([op, ord_item[1], qty])
            if len(valid) >= max_orders:
                break
        return valid

    @staticmethod
    def is_valid_coordinate(x: int, y: int, board_size: int = 10) -> bool:
        return 0 <= x < board_size and 0 <= y < board_size

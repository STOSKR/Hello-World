"""Pure business rules - Fee calculations and profit formulas"""

from typing import Literal


STEAM_FEE_PERCENT = 13.0
BUFF_FEE_PERCENT = 2.5

CNY_TO_EUR = 8.2  # 1 EUR = ~8.2 CNY (December 2025)


def calculate_fees(
    price: float, market: Literal["steam", "buff", "c5game", "uu"]
) -> float:
    if market == "steam":
        return price * (STEAM_FEE_PERCENT / 100)
    elif market == "buff":
        return price * (BUFF_FEE_PERCENT / 100)
    elif market in ("c5game", "uu"):
        # TODO: Add actual fees for C5GAME and UU when known
        return price * (BUFF_FEE_PERCENT / 100)
    else:
        raise ValueError(f"Unknown market: {market}")


def calculate_net_price(
    price: float, market: Literal["steam", "buff", "c5game", "uu"]
) -> float:
    fee = calculate_fees(price, market)
    return price - fee


def calculate_profit(buy_price: float, sell_price: float) -> float:
    cost_with_fees = buy_price
    revenue_after_fees = sell_price - calculate_fees(sell_price, "steam")

    return revenue_after_fees - cost_with_fees


def calculate_roi(buy_price: float, sell_price: float) -> float:
    profit = calculate_profit(buy_price, sell_price)
    investment = buy_price + calculate_fees(buy_price, "buff")

    if investment == 0:
        return 0.0

    return (profit / investment) * 100


def calculate_spread(steam_price: float, buff_price: float) -> float:
    return steam_price - buff_price


def is_profitable(
    buy_price: float, sell_price: float, min_roi_percent: float = 5.0
) -> bool:
    roi = calculate_roi(buy_price, sell_price)
    return roi >= min_roi_percent


def convert_cny_to_eur(price_cny: float) -> float:
    return price_cny / CNY_TO_EUR

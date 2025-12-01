"""Pure business rules - Fee calculations and profit formulas"""

from typing import Literal


# Market fees (constants)
STEAM_FEE_PERCENT = 13.0  # Steam takes 13% (5% Steam + 10% publisher)
BUFF_FEE_PERCENT = 2.5  # Buff163 takes 2.5%

# Currency conversion (update periodically)
CNY_TO_EUR = 8.1  # 1 EUR = ~8.1 CNY (December 2025)


def calculate_fees(
    price: float, market: Literal["steam", "buff", "c5game", "uu"]
) -> float:
    """Calculate marketplace fees

    Args:
        price: Item price before fees
        market: Marketplace name

    Returns:
        Fee amount

    Example:
        >>> calculate_fees(100.0, "steam")
        13.0
        >>> calculate_fees(100.0, "buff")
        2.5
    """
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
    """Calculate price after fees

    Args:
        price: Gross price
        market: Marketplace name

    Returns:
        Net price (after fees)
    """
    fee = calculate_fees(price, market)
    return price - fee


def calculate_profit(buy_price: float, sell_price: float) -> float:
    """Calculate net profit after fees

    Args:
        buy_price: Purchase price (e.g., from Buff)
        sell_price: Selling price (e.g., on Steam)

    Returns:
        Net profit in same currency

    Example:
        >>> calculate_profit(buy_price=100, sell_price=120)
        # Buy at Buff: 100 + 2.5% = 102.5
        # Sell on Steam: 120 - 13% = 104.4
        # Profit: 104.4 - 102.5 = 1.9
        1.9
    """
    # Cost with fees
    cost_with_fees = buy_price + calculate_fees(buy_price, "buff")

    # Revenue after fees
    revenue_after_fees = sell_price - calculate_fees(sell_price, "steam")

    return revenue_after_fees - cost_with_fees


def calculate_roi(buy_price: float, sell_price: float) -> float:
    """Calculate Return on Investment (ROI) as percentage

    Args:
        buy_price: Purchase price
        sell_price: Selling price

    Returns:
        ROI as percentage

    Example:
        >>> calculate_roi(100, 120)
        # Profit = 1.9, Investment = 102.5
        # ROI = (1.9 / 102.5) * 100 = 1.85%
        1.85
    """
    profit = calculate_profit(buy_price, sell_price)
    investment = buy_price + calculate_fees(buy_price, "buff")

    if investment == 0:
        return 0.0

    return (profit / investment) * 100


def calculate_spread(steam_price: float, buff_price: float) -> float:
    """Calculate raw price spread (before fees)

    Args:
        steam_price: Steam market price
        buff_price: Buff market price

    Returns:
        Price difference
    """
    return steam_price - buff_price


def is_profitable(
    buy_price: float, sell_price: float, min_roi_percent: float = 5.0
) -> bool:
    """Check if arbitrage is profitable above threshold

    Args:
        buy_price: Purchase price
        sell_price: Selling price
        min_roi_percent: Minimum ROI required

    Returns:
        True if ROI >= min_roi_percent
    """
    roi = calculate_roi(buy_price, sell_price)
    return roi >= min_roi_percent


def convert_cny_to_eur(price_cny: float) -> float:
    """Convert Chinese Yuan to Euro

    Args:
        price_cny: Price in CNY

    Returns:
        Price in EUR

    Example:
        >>> convert_cny_to_eur(73.0)
        10.0
    """
    return price_cny / CNY_TO_EUR

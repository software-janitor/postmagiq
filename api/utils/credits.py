"""Credit system utilities for converting costs to user-facing credits.

Credits provide a simplified way for regular users to understand usage
without exposing actual AI costs. Owners see actual costs; regular users see credits.

Default: 1 credit = $0.01 (so $5.00 = 500 credits)
"""

from decimal import Decimal
from typing import Optional

# Default conversion rate: 100 credits per dollar ($0.01 per credit)
DEFAULT_CREDITS_PER_DOLLAR = 100

# Default credit limit: 500 credits = $5.00
DEFAULT_CREDIT_LIMIT = 500


class CreditConfig:
    """Configuration for credit conversion and limits.

    In production, this would be stored in database and configurable by owner.
    For now, we use sensible defaults.
    """

    def __init__(
        self,
        credits_per_dollar: int = DEFAULT_CREDITS_PER_DOLLAR,
        default_credit_limit: int = DEFAULT_CREDIT_LIMIT,
    ):
        self.credits_per_dollar = credits_per_dollar
        self.default_credit_limit = default_credit_limit


# Global default config (can be replaced with DB-backed config later)
_default_config = CreditConfig()


def cost_to_credits(cost_usd: float, config: Optional[CreditConfig] = None) -> int:
    """Convert a USD cost to credits.

    Args:
        cost_usd: Cost in USD (e.g., 0.23 for 23 cents)
        config: Optional credit config, uses default if not provided

    Returns:
        Number of credits (integer, rounded up)
    """
    if config is None:
        config = _default_config

    # Convert to credits, rounding up to avoid giving free usage
    credits = Decimal(str(cost_usd)) * config.credits_per_dollar
    return int(credits.quantize(Decimal("1"), rounding="ROUND_UP"))


def credits_to_cost(credits: int, config: Optional[CreditConfig] = None) -> float:
    """Convert credits back to USD cost.

    Args:
        credits: Number of credits
        config: Optional credit config, uses default if not provided

    Returns:
        Cost in USD
    """
    if config is None:
        config = _default_config

    cost = Decimal(credits) / config.credits_per_dollar
    return float(cost.quantize(Decimal("0.01")))


def get_credit_limit(config: Optional[CreditConfig] = None) -> int:
    """Get the default credit limit.

    Args:
        config: Optional credit config, uses default if not provided

    Returns:
        Credit limit
    """
    if config is None:
        config = _default_config
    return config.default_credit_limit


def format_credits(credits: int) -> str:
    """Format credits for display.

    Args:
        credits: Number of credits

    Returns:
        Formatted string (e.g., "23 credits", "1 credit")
    """
    if credits == 1:
        return "1 credit"
    return f"{credits:,} credits"


def format_credit_usage(used: int, limit: int) -> str:
    """Format credit usage for display.

    Args:
        used: Credits used
        limit: Credit limit

    Returns:
        Formatted string (e.g., "23 / 500 credits used")
    """
    return f"{used:,} / {limit:,} credits used"

"""Budget enforcement for API costs.

Tracks spending and enforces budget limits to prevent runaway costs.

Usage:
    budget = BudgetEnforcer(
        daily_limit=10.0,  # $10/day
        monthly_limit=100.0,  # $100/month
    )

    # Check before calling
    if not budget.can_spend(estimated_cost):
        raise BudgetExceededError("Daily limit exceeded")

    # Record after calling
    budget.record_spend(actual_cost, model="claude-opus")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    """Raised when budget limit is exceeded."""

    def __init__(
        self,
        message: str,
        limit_type: str,
        limit: float,
        current: float,
    ):
        super().__init__(message)
        self.limit_type = limit_type
        self.limit = limit
        self.current = current


@dataclass
class BudgetConfig:
    """Configuration for budget enforcement.

    Attributes:
        daily_limit: Maximum spend per day (USD)
        monthly_limit: Maximum spend per month (USD)
        per_request_limit: Maximum cost per single request (USD)
        warning_threshold: Percentage of limit to trigger warning (0.0-1.0)
    """
    daily_limit: Optional[float] = None
    monthly_limit: Optional[float] = None
    per_request_limit: Optional[float] = None
    warning_threshold: float = 0.8  # Warn at 80%


@dataclass
class SpendRecord:
    """Record of a single API spend."""
    amount: float
    model: str
    timestamp: datetime
    metadata: dict = field(default_factory=dict)


# Model pricing (per 1M tokens, input/output)
MODEL_PRICING = {
    # Anthropic
    "claude-opus": {"input": 15.0, "output": 75.0},
    "claude-sonnet": {"input": 3.0, "output": 15.0},
    "claude-haiku": {"input": 0.25, "output": 1.25},
    # OpenAI
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    # Google
    "gemini-pro": {"input": 0.5, "output": 1.5},
    "gemini-flash": {"input": 0.075, "output": 0.3},
}


class BudgetEnforcer:
    """Enforces spending limits across API calls.

    Tracks daily and monthly spend, enforces limits, and provides
    cost estimation.

    Usage:
        budget = BudgetEnforcer(
            daily_limit=10.0,
            monthly_limit=100.0,
        )

        # Before API call
        estimated = budget.estimate_cost("claude-opus", 1000, 500)
        budget.check_budget(estimated)  # Raises if over limit

        # After API call
        budget.record_spend(actual_cost, "claude-opus")

        # Check status
        status = budget.get_status()
        print(f"Daily: ${status.daily_spend:.2f} / ${status.daily_limit:.2f}")
    """

    def __init__(self, config: Optional[BudgetConfig] = None, **kwargs):
        """Initialize budget enforcer.

        Args:
            config: BudgetConfig object
            **kwargs: Alternative to config (daily_limit, monthly_limit, etc.)
        """
        if config:
            self.config = config
        else:
            self.config = BudgetConfig(**kwargs)

        self._records: list[SpendRecord] = []
        self._daily_spend: float = 0.0
        self._monthly_spend: float = 0.0
        self._last_reset_daily: datetime = datetime.utcnow()
        self._last_reset_monthly: datetime = datetime.utcnow()

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost for a model call.

        Args:
            model: Model name (e.g., "claude-opus")
            input_tokens: Estimated input tokens
            output_tokens: Estimated output tokens

        Returns:
            Estimated cost in USD
        """
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            # Unknown model, use conservative estimate
            pricing = {"input": 15.0, "output": 75.0}
            logger.warning(f"Unknown model {model}, using conservative pricing")

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def can_spend(self, amount: float) -> bool:
        """Check if spending amount is within limits.

        Args:
            amount: Amount to spend in USD

        Returns:
            True if within all limits
        """
        self._reset_if_needed()

        # Check daily limit
        if self.config.daily_limit:
            if self._daily_spend + amount > self.config.daily_limit:
                return False

        # Check monthly limit
        if self.config.monthly_limit:
            if self._monthly_spend + amount > self.config.monthly_limit:
                return False

        # Check per-request limit
        if self.config.per_request_limit:
            if amount > self.config.per_request_limit:
                return False

        return True

    def check_budget(self, amount: float) -> None:
        """Check budget and raise if exceeded.

        Args:
            amount: Amount to spend in USD

        Raises:
            BudgetExceededError: If any limit would be exceeded
        """
        self._reset_if_needed()

        # Check per-request limit first
        if self.config.per_request_limit:
            if amount > self.config.per_request_limit:
                raise BudgetExceededError(
                    f"Request cost ${amount:.4f} exceeds per-request limit ${self.config.per_request_limit:.2f}",
                    limit_type="per_request",
                    limit=self.config.per_request_limit,
                    current=amount,
                )

        # Check daily limit
        if self.config.daily_limit:
            if self._daily_spend + amount > self.config.daily_limit:
                raise BudgetExceededError(
                    f"Daily limit exceeded: ${self._daily_spend:.2f} + ${amount:.4f} > ${self.config.daily_limit:.2f}",
                    limit_type="daily",
                    limit=self.config.daily_limit,
                    current=self._daily_spend,
                )

            # Check warning threshold
            threshold = self.config.daily_limit * self.config.warning_threshold
            if self._daily_spend + amount > threshold:
                logger.warning(
                    f"Approaching daily limit: ${self._daily_spend + amount:.2f} / ${self.config.daily_limit:.2f}"
                )

        # Check monthly limit
        if self.config.monthly_limit:
            if self._monthly_spend + amount > self.config.monthly_limit:
                raise BudgetExceededError(
                    f"Monthly limit exceeded: ${self._monthly_spend:.2f} + ${amount:.4f} > ${self.config.monthly_limit:.2f}",
                    limit_type="monthly",
                    limit=self.config.monthly_limit,
                    current=self._monthly_spend,
                )

            # Check warning threshold
            threshold = self.config.monthly_limit * self.config.warning_threshold
            if self._monthly_spend + amount > threshold:
                logger.warning(
                    f"Approaching monthly limit: ${self._monthly_spend + amount:.2f} / ${self.config.monthly_limit:.2f}"
                )

    def record_spend(
        self,
        amount: float,
        model: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Record an actual spend.

        Args:
            amount: Amount spent in USD
            model: Model used
            metadata: Additional metadata (user_id, workspace_id, etc.)
        """
        self._reset_if_needed()

        record = SpendRecord(
            amount=amount,
            model=model,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )
        self._records.append(record)

        self._daily_spend += amount
        self._monthly_spend += amount

        logger.debug(f"Recorded spend: ${amount:.4f} for {model}")

    def get_status(self) -> dict:
        """Get current budget status.

        Returns:
            Dict with spend and limit information
        """
        self._reset_if_needed()

        return {
            "daily_spend": self._daily_spend,
            "daily_limit": self.config.daily_limit,
            "daily_remaining": (
                self.config.daily_limit - self._daily_spend
                if self.config.daily_limit else None
            ),
            "monthly_spend": self._monthly_spend,
            "monthly_limit": self.config.monthly_limit,
            "monthly_remaining": (
                self.config.monthly_limit - self._monthly_spend
                if self.config.monthly_limit else None
            ),
            "total_records": len(self._records),
        }

    def get_spend_by_model(self) -> dict[str, float]:
        """Get spend breakdown by model.

        Returns:
            Dict mapping model name to total spend
        """
        spend_by_model: dict[str, float] = {}
        for record in self._records:
            spend_by_model[record.model] = (
                spend_by_model.get(record.model, 0.0) + record.amount
            )
        return spend_by_model

    def _reset_if_needed(self) -> None:
        """Reset counters if time period has passed."""
        now = datetime.utcnow()

        # Reset daily spend
        if now.date() > self._last_reset_daily.date():
            logger.info(f"Resetting daily spend (was ${self._daily_spend:.2f})")
            self._daily_spend = 0.0
            self._last_reset_daily = now

        # Reset monthly spend
        if now.month != self._last_reset_monthly.month or now.year != self._last_reset_monthly.year:
            logger.info(f"Resetting monthly spend (was ${self._monthly_spend:.2f})")
            self._monthly_spend = 0.0
            self._last_reset_monthly = now


# Default budget configurations
DEFAULT_BUDGET = BudgetConfig(
    daily_limit=5.0,
    monthly_limit=50.0,
    per_request_limit=1.0,
)

GENEROUS_BUDGET = BudgetConfig(
    daily_limit=50.0,
    monthly_limit=500.0,
    per_request_limit=5.0,
)

STRICT_BUDGET = BudgetConfig(
    daily_limit=1.0,
    monthly_limit=10.0,
    per_request_limit=0.25,
)

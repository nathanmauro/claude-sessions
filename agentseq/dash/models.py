"""Dash-only pydantic DTOs.

These model external/untrusted payloads (Notion API rows, the subscription
usage JSON) where pydantic's nested validation and coercion earn their keep.
The dash package is allowed third-party deps; core stays pydantic-free.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class NotionTodo(BaseModel):
    name: str = ""
    status: str = ""
    due: str | None = None
    url: str | None = None
    project: str = ""
    source: str = ""


class NotionTodosResult(BaseModel):
    todos: list[NotionTodo] = Field(default_factory=list)
    source: Literal["live", "cache", "none"] = "none"
    fetched_at: str | None = None


class RateLimit(BaseModel):
    used_percentage: float | None = None
    resets_at: int | float | str | None = None
    reset_at: int | float | str | None = None


class RateLimits(BaseModel):
    five_hour: RateLimit | None = None
    seven_day: RateLimit | None = None
    seven_day_opus: RateLimit | None = None
    seven_day_sonnet: RateLimit | None = None


class SubscriptionCost(BaseModel):
    total_cost_usd: float | None = None


class SubscriptionUsage(BaseModel):
    rate_limits: RateLimits | None = None
    cost: SubscriptionCost | None = None

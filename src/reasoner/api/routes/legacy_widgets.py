"""Legacy widget endpoints (weather, stocks, calculator, discover)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from reasoner.api.schemas import CalculationRequest, DiscoverRequest, StockRequest, WeatherRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/weather")
async def get_weather(location: str = ""):
    """Get weather data for a location (legacy endpoint)."""
    if not location:
        raise HTTPException(status_code=400, detail="Location parameter required")
    try:
        from reasoner.widgets import get_weather_data

        weather_data = await get_weather_data(location)
        return weather_data
    except Exception as e:
        logger.error(f"Weather error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/stocks")
async def get_stock(symbol: str = ""):
    """Get stock data for a symbol (legacy endpoint)."""
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol parameter required")
    try:
        from reasoner.widgets import get_stock_data

        stock_data = get_stock_data(symbol.upper())
        return stock_data
    except Exception as e:
        logger.error(f"Stock error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/calculate")
async def calculate(req: CalculationRequest):
    """Evaluate a mathematical expression (legacy endpoint)."""
    try:
        from reasoner.widgets import calculate_expression

        result = calculate_expression(req.expression)
        return result
    except Exception as e:
        logger.error(f"Calculation error: {e}")
        return {"error": str(e), "valid": False}


@router.get("/api/discover")
async def discover(topic: str = "tech", mode: str = "normal"):
    """Get trending content for a topic (legacy endpoint)."""
    try:
        from reasoner.widgets import get_discover_content

        content = await get_discover_content(topic, mode)
        return content
    except Exception as e:
        logger.error(f"Discover error: {e}")
        return {"error": str(e), "results": []}

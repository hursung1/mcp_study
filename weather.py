from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather")

NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

# functions
async def make_nws_request(url: str) -> dict[str, Any] | None:
    """
    뉴스 api 요청을 보내고 응답을 반환
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json",
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
        
def format_alert(feature: dict) -> str:
    """
    Feature를 가공하여 읽기 좋은 형태로 변환
    """
    props = feature["properties"]
    return f"""
Event: {props.get("event", "Unknown")}
Area: {props.get("areaDesc", "Unknown")}
Serverity: {props.get("severity", "Unknown")}
Description:: {props.get("description", "No description available")}
Instructions: {props.get("instruction", "No instructions available")}
"""

# tool execution
@mcp.tool()
async def get_alerts(state: str) -> str:
    """
    미국 각 주에 대한 날씨 알림을 가져옴
    state: 알파벳 두 글자로 된 미국 주 코드
    """

    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)
    if not data or "features" not in data:
        return "알림을 받아올 수 없거나 지정된 알림이 없습니다."
    if not data["features"]:
        return "입력된 주에 대한 알림이 없습니다."
    
    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """
    미국의 특정 위치에 대한 날씨 예보를 가져옴
    latitude: 위도
    longitude: 경도
    """
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "입력된 위치에 대한 날씨 정보를 가져올 수 없음"
    
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "자세한 날씨 예보를 가져올 수 없음"
    
    # 기간 정보를 읽기 쉽게 변환
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)
    
    return "\n---\n".join(forecasts)


if __name__ == "__main__":
    mcp.run(transport="stdio")
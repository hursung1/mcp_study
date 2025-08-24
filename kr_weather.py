import asyncio
from typing import Any
import httpx
import os
import ssl
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from datetime import datetime
import pandas as pd

mcp = FastMCP("weather")

API_URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
USER_AGENT = "weather-app/1.0"

load_dotenv()
service_key = os.getenv("KOR_WEATHER_API")

precipitation_type_dict = {
    "0": "없음",
    "1": "비",
    "2": "비/눈",
    "3": "눈",
    "4": "소나기",
    "5": "빗방울",
    "6": "빗방울눈날림",
    "7": "눈날림",
}

# functions

def get_current_date_and_time():
    """현재 날짜 및 시간을 yyyyMMdd / hhmm 형식으로 반환"""
    return datetime.now().strftime('%Y%m%d'), datetime.now().strftime('%H%M')

def convert_location(latitude: float, longitude: float) -> tuple[str, str, str, int, int]:
    """
    한국의 특정 위치 이름을 받아 위도와 경도를 반환
    """
    location_df = pd.read_csv("kor_loc_info.csv")
    loc_x_hour = int(latitude)
    loc_y_hour = int(longitude)

    loc_x_min = ((latitude - loc_x_hour) * 3600 ) // 60
    loc_y_min = ((longitude - loc_y_hour) * 3600 ) // 60

    for row in location_df.itertuples():
        if (row.latitude_h == loc_x_hour and row.latitude_m == loc_x_min) and\
             (row.longitude_h == loc_y_hour and row.longitude_m == loc_y_min):
            return row.level1, row.level2, row.level3, row.x, row.y

    return None, None, None, None, None


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """
    날씨 api 요청을 보내고 응답을 반환
    """
    print(service_key)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # SSL 컨텍스트 설정
    # 더 관대한 SSL 설정
    ssl_context = ssl.create_default_context()
    ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')

    async with httpx.AsyncClient(verify=ssl_context, http2=False) as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(e)
            return None
        
async def format_forecast(feature: dict) -> str:
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
async def get_current_forecast(latitude: float, longitude: float) -> str:
    """
    한국의 특정 위치에 대한 지금 현재의 날씨 예보를 가져옴 (초단기실황 예보)
    loc_name: 한국의 특정 위치 이름 
    """
    loc_level1, loc_level2, loc_level3, loc_x, loc_y = convert_location(latitude, longitude)
    date, time = get_current_date_and_time()
    # time = "0600"
    print(f"행정구역 정보: {loc_level1}, {loc_level2}, {loc_level3}")
    print(f"현재 날짜 및 시간: {date} {time}")
    forecast_url = f"{API_URL}?serviceKey={service_key}&dataType=JSON&base_date={date}&base_time={time}&nx={loc_x}&ny={loc_y}"
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "자세한 날씨 예보를 가져올 수 없음"
    
    # 기간 정보를 읽기 쉽게 변환
    # print(forecast_data)
    for datum in forecast_data["response"]["body"]["items"]["item"]:
        if datum["category"] == "T1H": # 기온
            temperature = datum["obsrValue"]
        elif datum["category"] == "RN1": # 강수량
            precipitation = datum["obsrValue"]
        elif datum["category"] == "UUU": # 동서바람성분
            wind_speed_east_west = datum["obsrValue"]
        elif datum["category"] == "VVV": # 남북바람성분
            wind_speed_north_south = datum["obsrValue"]
        elif datum["category"] == "REH": # 습도
            humidity = datum["obsrValue"]
        elif datum["category"] == "PTY": # 강수형태
            precipitation_type_cd = datum["obsrValue"]
            precipitation_type = precipitation_type_dict[precipitation_type_cd]
        elif datum["category"] == "VEC": # 풍향
            wind_direction = datum["obsrValue"]
        elif datum["category"] == "WSD": # 풍속
            wind_speed = datum["obsrValue"]
        
    return f"""
기온: {temperature}°C
풍속: {wind_speed} m/s
풍향: {wind_direction}
습도: {humidity}%
강수량: {precipitation} mm
강수형태: {precipitation_type}
"""

@mcp.tool()
async def get_week_forecast(latitude: float, longitude: float) -> str:
    """
    한국의 특정 위치에 대한 주간 날씨 예보를 가져옴
    latitude: 위도
    longitude: 경도
    """
    current_date, _ = get_current_date_and_time()
    current_forecast = await get_current_forecast(current_date, latitude, longitude)

    
if __name__ == "__main__":
    # current_forecast = asyncio.run(get_current_forecast(35.1796, 129.0756))
    # print(current_forecast)
    mcp.run(transport="stdio")
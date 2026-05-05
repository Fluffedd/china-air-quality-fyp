# async API client using aiohttp
import asyncio
import aiohttp
import os
from datetime import datetime
from typing import List, Optional
from .config import CITY_CN_MAP


async def fetch_one(session, city: str, token: Optional[str] = None):
    api_token = token or os.environ.get("WAQI_TOKEN") or os.getenv("WAQI_TOKEN")
    url = f"https://api.waqi.info/feed/{city}/?token={api_token or ''}"
    try:
        async with session.get(url, timeout=10) as resp:
            js = await resp.json()
            if js.get("status") != "ok":
                return None
            d = js["data"]
            return {
                "city_en": city,
                "city_cn": CITY_CN_MAP.get(city, city),
                "aqi": (int(d.get("aqi")) if str(d.get("aqi")).isdigit() else None),
                "pm25": d.get("iaqi", {}).get("pm25", {}).get("v"),
                "pm10": d.get("iaqi", {}).get("pm10", {}).get("v"),
                "o3": d.get("iaqi", {}).get("o3", {}).get("v"),
                "no2": d.get("iaqi", {}).get("no2", {}).get("v"),
                "so2": d.get("iaqi", {}).get("so2", {}).get("v"),
                "co": d.get("iaqi", {}).get("co", {}).get("v"),
                "dominent": d.get("dominentpol"),
                "update_time": d.get("time", {}).get("s"),
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    except Exception:
        return None


async def fetch_all_async(
    city_list: List[str], concurrency: int = 30, token: Optional[str] = None
):
    connector = aiohttp.TCPConnector(limit_per_host=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_one(session, c, token=token) for c in city_list]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    return [r for r in results if r]




def batch_fetch(city_list: List[str], concurrency: int = 30, token: Optional[str] = None):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(
        fetch_all_async(city_list, concurrency=concurrency, token=token)
    )
    loop.close()
    return res
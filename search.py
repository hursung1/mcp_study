from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import requests
import asyncio
import weaviate
import weaviate.classes.query as wq

mcp = FastMCP("search")

news_api_id = "ZG0zAKuFV7KrqQppPRBS"
news_api_key = "5h24Rk21hJ"

class NaverNewsAPI:
    def __init__(self, client_id="ZG0zAKuFV7KrqQppPRBS", client_secret="5h24Rk21hJ"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.url = "https://openapi.naver.com/v1/search/news.json"

    def get_news(self, query):
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret}
        response = requests.get(self.url, headers=headers, params={"query": query})
        return response.json()["items"]


async def make_nws_request(url: str, query: str) -> dict[str, Any] | None:
    """
    뉴스 api 요청을 보내고 응답을 반환
    """
    headers = {
        "X-Naver-Client-Id": news_api_id,
        "X-Naver-Client-Secret": news_api_key,
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params={"query": query}, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


async def vectorize(input_str: str) -> list[float]:
    """
    Genos에 올라간 embedding 호출하여 vectorize
    """

    emb_url = "https://genos.mnc.ai:3443/api/gateway/rep/serving/10/v1/embeddings"
    emb_key = "d2278640406c48b1b626ae5963fa25a1"
    emb_headers = {
        "Content-Type": "application/json", "Authorization": f"Bearer {emb_key}"
    }
    input_data = {
        "input": [input_str]
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url=emb_url, headers=emb_headers, json=input_data)
            return response.json()["data"][0]["embedding"]
        
        except Exception as e:
            print(f"Error in vectorize: {str(e)}")
            return None


@mcp.tool()
async def get_news(query: str) -> str:
    """
    뉴스 api를 통해 사용자의 질문(query)에 대한 뉴스를 검색하여 가져옴
    """
    url = f"https://openapi.naver.com/v1/search/news.json"
    data = await make_nws_request(url, query)
    if not data or "items" not in data:
        return "뉴스를 받아올 수 없거나 지정된 뉴스가 없습니다."
    
    # articles = [f"{item['title']}: {item['description']}\nlink: {item['link']}" for item in data["items"]]
    articles = [f"{item['title']}: {item['description']}" for item in data["items"]]
    return "\n---\n".join(articles)


@mcp.tool()
async def do_rag(query: str) -> str:
    """
    사내/사외 규정, 매뉴얼, 회의록 등의 내용에 대한 사용자의 질의를 처리하고 답변을 생성하기 위해 rag를 수행
    """
    async with weaviate.use_async_with_local() as async_client:
        db = async_client.collections.get("MiraeNVTest")
        query_vector = await vectorize(query)

        search_result = await db.query.hybrid(
            query=query, 
            vector=query_vector,
            limit=5,
        )

    chunk_texts = [obj.properties["text"] for obj in search_result.objects]

    # client.close()
    return "\n---\n".join(chunk_texts)


if __name__ == "__main__":
    mcp.run(transport="stdio")
    # out = asyncio.run(do_rag("22년 7월 STR 회의"))
    # print(out)

import asyncio

class DiscoveryClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

_default_client = None

async def get_discovery_client(base_url: str | None = None):
    global _default_client
    if _default_client is None:
        _default_client = DiscoveryClient(base_url=base_url or "http://default")
    return _default_client

async def test_client():
    c1 = await get_discovery_client("http://A")
    print(f"Client 1 URL: {c1.base_url}")
    
    c2 = await get_discovery_client("http://B")
    print(f"Client 2 URL: {c2.base_url}")
    
    print(f"{'FAIL' if c2.base_url == 'http://A' else 'PASS'}")

if __name__ == "__main__":
    asyncio.run(test_client())

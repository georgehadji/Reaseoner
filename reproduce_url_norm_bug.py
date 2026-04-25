
def _normalize_url(url: str) -> str:
    if not url:
        return ""
    # Current implementation
    u = url.lower().split("://")[-1].split("#")[0].rstrip("/")
    if u.startswith("www."):
        u = u[4:]
    return u

def test_norm():
    test_cases = [
        ("https://example.com/path/", "https://example.com/path"), # Should be equal
        ("https://example.com/path/?a=1", "https://example.com/path?a=1"), # Should be equal
    ]
    
    for u1, u2 in test_cases:
        n1 = _normalize_url(u1)
        n2 = _normalize_url(u2)
        print(f"URL 1: {u1} -> {n1}")
        print(f"URL 2: {u2} -> {n2}")
        print(f"Equal: {n1 == n2} | {'PASS' if n1 == n2 else 'FAIL'}")

if __name__ == "__main__":
    test_norm()

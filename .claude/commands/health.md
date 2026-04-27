# /health — API Health Check

Check if the Reasoner backend is running and healthy.

```bash
curl -s http://localhost:8003/health | python -m json.tool 2>/dev/null || echo "Backend not running. Start with: python start_all.py"
```

Also verify frontend:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>/dev/null | grep -q "200" && echo "Frontend: OK (port 3000)" || echo "Frontend not running. Start with: cd ui-next && npm run dev"
```

If backend is down, start everything:
```bash
python start_all.py
```

# Start Reasoner Server
# Run this script to start the Reasoner API server

import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("  Reasoner - AI Reasoning Platform")
    print("=" * 60)
    print()
    print("Starting server on http://localhost:8000")
    print()
    print("Available endpoints:")
    print("  - POST /api/run             Run pipeline")
    print("  - GET  /api/presets         List presets")
    print("  - GET  /api/models          List models")
    print("  - WS   /ws                  WebSocket for real-time updates")
    print()
    print("Press Ctrl+C to stop")
    print()
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )

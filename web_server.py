import os
import uvicorn
from backend.web_server import app

if __name__ == "__main__":
    uvicorn.run(
        "backend.web_server:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )

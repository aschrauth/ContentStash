"""
Entry point for running the FastAPI application with uvicorn.
This allows starting the backend with: python main.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
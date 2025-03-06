import uvicorn
import os

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

if __name__ == "__main__":
    print("Starting AI Assistant Framework...")
    print("Make sure LMStudio is running with API server enabled at http://localhost:1234")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
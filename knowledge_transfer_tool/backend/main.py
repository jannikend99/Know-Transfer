from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os # Import os module

from .database import engine #, SessionLocal # SessionLocal might be used later for dependencies
from .models import Base # Import Base from models

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Determine the path to the static directory relative to this main.py file
# __file__ is the path to the current file (main.py)
# os.path.dirname(__file__) is the directory of main.py (backend/)
# os.path.join(os.path.dirname(__file__), "static") is backend/static/
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
# The actual assets (js, css) are in a nested 'static' folder after CRA build and copy
CRA_STATIC_ASSETS_DIR = os.path.join(STATIC_DIR, "static")

# API routes first (higher priority)
from .routers import api_router # Import the api_router
app.include_router(api_router, prefix="/api")

# Serve static files: any URL starting with /static/ will be looked for in CRA_STATIC_ASSETS_DIR
app.mount("/static", StaticFiles(directory=CRA_STATIC_ASSETS_DIR), name="cra_static_assets")

# Catch-all route for React Router (SPA) - serves index.html from the root of STATIC_DIR
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    index_path = os.path.join(STATIC_DIR, "index.html")
    # Check if the file exists to prevent errors if index.html is missing
    if not os.path.exists(index_path):
        # Provide a more specific error or a generic 404 page if index.html is truly missing
        return FileResponse(os.path.join(STATIC_DIR, "404.html"), status_code=404) # Assuming you add a 404.html
    return FileResponse(index_path)

# Remove the uvicorn.run block if present, as run.py now handles it
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000) 
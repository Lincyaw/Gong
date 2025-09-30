"""
Main entry point for the simulation platform.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("platform.api.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")

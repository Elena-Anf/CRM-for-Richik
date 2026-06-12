"""Quick start script.
Usage:
  python run.py          # start server
  python run.py seed     # seed database
"""
import sys
import uvicorn


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        from seed import seed
        import asyncio
        asyncio.run(seed())
        return

    print("Starting Grooming CRM...")
    print("  http://localhost:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()

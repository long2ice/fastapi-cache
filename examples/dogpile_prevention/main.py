"""Example demonstrating dogpile prevention in fastapi-cache."""
import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import HTMLResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from starlette.requests import Request
from starlette.responses import Response

# Track computation times for demonstration
computation_tracker = {}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Initialize cache with dogpile prevention enabled
    FastAPICache.init(
        InMemoryBackend(),
        prefix="dogpile-demo",
        enable_dogpile_prevention=True,
        dogpile_grace_time=30.0,  # Allow 30 seconds for computation
        dogpile_wait_time=0.1,    # Check every 100ms
        dogpile_max_wait_time=5.0,  # Wait max 5 seconds
    )
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    """Home page with example links."""
    return HTMLResponse("""
    <html>
    <head>
        <title>Dogpile Prevention Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .button {
                display: inline-block;
                padding: 10px 20px;
                margin: 5px;
                background-color: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 4px;
            }
            .info {
                background-color: #f0f0f0;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }
            pre { background-color: #f5f5f5; padding: 10px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>FastAPI Cache - Dogpile Prevention Demo</h1>

        <div class="info">
            <h2>What is Dogpile Prevention?</h2>
            <p>Dogpile prevention (also known as cache stampede prevention) ensures that when multiple
            requests arrive for the same uncached resource, only one request computes the value while
            others wait for the result.</p>
        </div>

        <h2>Examples:</h2>

        <h3>1. Expensive Computation (3 seconds)</h3>
        <a class="button" href="/expensive/1" target="_blank">Request Item 1</a>
        <a class="button" href="/expensive/2" target="_blank">Request Item 2</a>
        <p>Try opening multiple tabs quickly for the same item!</p>

        <h3>2. Without Dogpile Prevention</h3>
        <a class="button" href="/no-dogpile/1" target="_blank">Request Item 1 (No Protection)</a>
        <p>Compare the behavior when dogpile prevention is disabled.</p>

        <h3>3. Simulate Concurrent Requests</h3>
        <a class="button" href="/simulate-concurrent/1">Simulate 5 Concurrent Requests</a>
        <p>This will simulate 5 concurrent requests for the same resource.</p>

        <h3>4. View Statistics</h3>
        <a class="button" href="/stats">View Computation Statistics</a>
        <a class="button" href="/clear-stats">Clear Statistics</a>

        <script>
            // Auto-refresh stats every 2 seconds if on stats page
            if (window.location.pathname === '/stats') {
                setTimeout(() => location.reload(), 2000);
            }
        </script>
    </body>
    </html>
    """)


@app.get("/expensive/{item_id}")
@cache(expire=60)  # Cache for 60 seconds
async def expensive_computation(item_id: int, request: Request, response: Response):
    """Simulate an expensive computation with dogpile prevention."""
    start_time = time.time()

    # Track when computation starts
    key = f"expensive_{item_id}"
    if key not in computation_tracker:
        computation_tracker[key] = []
    computation_tracker[key].append({
        "start_time": start_time,
        "status": "started"
    })

    # Simulate expensive computation
    await asyncio.sleep(3.0)

    # Mark computation as complete
    computation_tracker[key][-1]["end_time"] = time.time()
    computation_tracker[key][-1]["status"] = "completed"
    computation_tracker[key][-1]["duration"] = computation_tracker[key][-1]["end_time"] - start_time

    return {
        "item_id": item_id,
        "data": f"Expensive result for item {item_id}",
        "computed_at": time.time(),
        "computation_time": 3.0
    }


@app.get("/no-dogpile/{item_id}")
@cache(expire=60, enable_dogpile_prevention=False)  # Explicitly disable dogpile prevention
async def no_dogpile_computation(item_id: int):
    """Same expensive computation but without dogpile prevention."""
    start_time = time.time()

    # Track computation
    key = f"no_dogpile_{item_id}"
    if key not in computation_tracker:
        computation_tracker[key] = []
    computation_tracker[key].append({
        "start_time": start_time,
        "status": "started"
    })

    # Simulate expensive computation
    await asyncio.sleep(3.0)

    # Mark completion
    computation_tracker[key][-1]["end_time"] = time.time()
    computation_tracker[key][-1]["status"] = "completed"
    computation_tracker[key][-1]["duration"] = computation_tracker[key][-1]["end_time"] - start_time

    return {
        "item_id": item_id,
        "data": f"Result for item {item_id} (no dogpile prevention)",
        "computed_at": time.time(),
        "computation_time": 3.0
    }


async def make_request(item_id: int):
    """Helper to simulate a request to the expensive endpoint."""
    # In a real scenario, this would be an HTTP request
    # For demo purposes, we'll call the function directly
    request = Request({"type": "http", "method": "GET", "url": f"/expensive/{item_id}"})
    response = Response()
    return await expensive_computation(item_id, request, response)


@app.get("/simulate-concurrent/{item_id}")
async def simulate_concurrent_requests(item_id: int, background_tasks: BackgroundTasks):
    """Simulate multiple concurrent requests for the same resource."""
    # Clear previous stats for this item
    key = f"concurrent_{item_id}"
    computation_tracker[key] = {
        "start_time": time.time(),
        "requests": 5,
        "status": "started"
    }

    # Start 5 concurrent tasks
    tasks = []
    for i in range(5):
        # Add small delays to simulate realistic request timing
        await asyncio.sleep(0.05 * i)
        tasks.append(asyncio.create_task(make_request(item_id)))

    # Wait for all to complete
    results = await asyncio.gather(*tasks)

    computation_tracker[key]["end_time"] = time.time()
    computation_tracker[key]["duration"] = computation_tracker[key]["end_time"] - computation_tracker[key]["start_time"]
    computation_tracker[key]["status"] = "completed"

    # Count unique computation times (should be 1 with dogpile prevention)
    unique_computations = len({r["computed_at"] for r in results})

    return {
        "item_id": item_id,
        "total_requests": 5,
        "unique_computations": unique_computations,
        "dogpile_prevented": unique_computations == 1,
        "total_time": computation_tracker[key]["duration"],
        "message": f"{'✅ Dogpile prevention worked!' if unique_computations == 1 else '❌ Multiple computations occurred'}"
    }


@app.get("/stats")
async def view_stats():
    """View computation statistics."""
    stats_html = """
    <html>
    <head>
        <title>Computation Statistics</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #4CAF50; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .back-button {
                display: inline-block;
                padding: 10px 20px;
                margin: 10px 0;
                background-color: #008CBA;
                color: white;
                text-decoration: none;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <h1>Computation Statistics</h1>
        <a class="back-button" href="/">← Back to Home</a>

        <h2>Computation History</h2>
        <table>
            <tr>
                <th>Resource</th>
                <th>Start Time</th>
                <th>Duration</th>
                <th>Status</th>
                <th>Total Computations</th>
            </tr>
    """

    for key, computations in computation_tracker.items():
        if isinstance(computations, list):
            for comp in computations:
                start_time = time.strftime('%H:%M:%S', time.localtime(comp['start_time']))
                duration = f"{comp.get('duration', 'N/A'):.2f}s" if 'duration' in comp else 'In Progress'
                stats_html += f"""
                <tr>
                    <td>{key}</td>
                    <td>{start_time}</td>
                    <td>{duration}</td>
                    <td>{comp['status']}</td>
                    <td>{len(computations)}</td>
                </tr>
                """

    stats_html += """
        </table>

        <h2>Summary</h2>
        <ul>
    """

    # Add summary statistics
    with_dogpile = sum(1 for k in computation_tracker.keys() if k.startswith('expensive_'))
    without_dogpile = sum(1 for k in computation_tracker.keys() if k.startswith('no_dogpile_'))

    stats_html += f"""
            <li>Resources with dogpile prevention: {with_dogpile}</li>
            <li>Resources without dogpile prevention: {without_dogpile}</li>
        </ul>

        <p><em>Page auto-refreshes every 2 seconds</em></p>
    </body>
    </html>
    """

    return HTMLResponse(stats_html)


@app.get("/clear-stats")
async def clear_stats():
    """Clear computation statistics."""
    computation_tracker.clear()
    return {"message": "Statistics cleared", "redirect": "/"}


@app.get("/clear-cache")
async def clear_cache():
    """Clear all cached data."""
    await FastAPICache.clear()
    return {"message": "Cache cleared", "items_cleared": "all"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

@echo off
echo Starting OEE Tracker Backend (FastAPI)...
start cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn oee_tracker.backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting OEE Tracker Frontend (Vite)...
start cmd /k "cd oee_tracker\frontend && npm run dev"

echo Both services have been started in separate windows!
pause

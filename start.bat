@echo off
cd /d "D:\ИИ\Code\CRM for Richik"
echo Starting Grooming CRM...
echo Open http://localhost:8000 in your browser
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause

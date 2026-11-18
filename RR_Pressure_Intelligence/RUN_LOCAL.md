# RR Pressure Intelligence — Local Run

## Included
- FastAPI backend and React frontend
- Generated analytics outputs for the official SupeRR Selector Season 2 data pack
- Dataset version: `6ffc18bfb9`
- Original six CSV source files in `backend/datasets/source_data/`

## 1. Backend
Create `backend/.env` from `backend/.env.example` and set your own MongoDB connection string.

PowerShell:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

The generated outputs and registry are already included in `backend/outputs/`, so you do not need to rerun the analytics pipeline for the included dataset.

## 2. Frontend
Create `frontend/.env` from `frontend/.env.example`.

In a second terminal:
```powershell
cd frontend
yarn install
yarn start
```

Open `http://localhost:3000`.

## 3. Re-run analytics from the included official data
From the `backend` directory, with the virtual environment activated:
```powershell
python -m analytics.run datasets/source_data outputs
```
This creates a new versioned output folder and updates `outputs/registry.json`.

## Notes
- Keep the backend and frontend terminals running simultaneously.
- Do not commit or share your real `backend/.env` credentials.
- The API is at `http://127.0.0.1:8000`; Swagger docs are at `http://127.0.0.1:8000/docs`.

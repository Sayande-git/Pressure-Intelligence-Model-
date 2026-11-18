import asyncio
import json
import logging
import os
import shutil
import tempfile
import zipfile
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from pymongo import ASCENDING, IndexModel
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
OUT = ROOT_DIR / "outputs"
DATA = ROOT_DIR / "datasets"
INDEXES = {"eligibility_overrides": [IndexModel([("player_id", ASCENDING)], name="player_id", unique=True)]}
JSON_FILES = {"overview", "audit", "eligibility", "pressure", "batting", "bowling", "venues", "requirements"}
EXPORTS = {"methodology_report.pdf", "batting_rankings.csv", "bowling_rankings.csv", "player_eligibility.csv", "venues.csv", "engineered_deliveries.csv.gz"}
JOB = {"state": "idle", "message": "", "version": None}
_cache: dict = {}

app = FastAPI()
api = APIRouter(prefix="/api")


def registry():
    p = OUT / "registry.json"
    return json.loads(p.read_text()) if p.exists() else {"versions": [], "current": None}


def current_dir(version: str | None = None):
    v = version or registry()["current"]
    if not v or not (OUT / v).exists():
        raise HTTPException(404, "No analysed dataset available")
    return OUT / v


@api.get("/")
async def root():
    return {"service": "RR Pressure Intelligence", "current_version": registry()["current"]}


@api.get("/data/{name}")
async def get_data(name: str, version: str | None = None):
    if name not in JSON_FILES:
        raise HTTPException(404, "Unknown dataset")
    p = current_dir(version) / f"{name}.json"
    key = (str(p), p.stat().st_mtime)
    if key not in _cache:
        _cache[key] = json.loads(p.read_text())
    return _cache[key]


@api.get("/export/{fname}")
async def export(fname: str, version: str | None = None):
    if fname not in EXPORTS:
        raise HTTPException(404, "Unknown export")
    p = current_dir(version) / fname
    if not p.exists():
        raise HTTPException(404, "Export not generated")
    return FileResponse(p, filename=fname)


@api.get("/versions")
async def versions():
    r = registry()
    return {"current": r["current"], "versions": [{k: v for k, v in x.items() if k != "schema"} for x in r["versions"]], "job": JOB}


class Override(BaseModel):
    player_id: int
    status: Literal["Eligible", "Ineligible", "Unverified"]
    note: str = ""


@api.get("/eligibility/overrides")
async def list_overrides():
    return await db.eligibility_overrides.find({}, {"_id": 0}).to_list(5000)


@api.post("/eligibility/overrides")
async def set_override(o: Override):
    doc = {**o.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.eligibility_overrides.update_one({"player_id": o.player_id}, {"$set": doc}, upsert=True)
    return doc


@api.delete("/eligibility/overrides/{player_id}")
async def delete_override(player_id: int):
    await db.eligibility_overrides.delete_one({"player_id": player_id})
    return {"deleted": player_id}


def _run_pipeline(raw_dir: Path):
    from analytics.run import run
    try:
        JOB.update(state="running", message="Re-running audit, pressure engine, ratings, validation and report")
        v = run(raw_dir, OUT)
        JOB.update(state="done", message="Analysis regenerated", version=v)
    except Exception as e:  # surface pipeline failure to the UI
        logging.exception("pipeline failed")
        JOB.update(state="error", message=str(e)[:400])


@api.post("/dataset/upload")
async def upload(file: UploadFile = File(...)):
    if JOB["state"] == "running":
        raise HTTPException(409, "A pipeline run is already in progress")
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "Upload a .zip data pack")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    dest = DATA / f"upload_{stamp}"
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        tmp.write(await file.read())
        tmp.flush()
        try:
            with zipfile.ZipFile(tmp.name) as z:
                for m in z.namelist():
                    if m.lower().endswith(".csv") and not m.startswith("__MACOSX"):
                        (dest / Path(m).name).write_bytes(z.read(m))
        except zipfile.BadZipFile:
            shutil.rmtree(dest)
            raise HTTPException(400, "Invalid zip file")
    if not any(dest.glob("*.csv")):
        shutil.rmtree(dest)
        raise HTTPException(400, "Zip contains no CSV files")
    asyncio.get_running_loop().run_in_executor(None, _run_pipeline, dest)
    return {"status": "started", "files": sorted(p.name for p in dest.glob("*.csv"))}


@api.post("/versions/{version}/activate")
async def activate(version: str):
    r = registry()
    if version not in [v["version"] for v in r["versions"]]:
        raise HTTPException(404, "Unknown version")
    r["current"] = version
    (OUT / "registry.json").write_text(json.dumps(r))
    return {"current": version}


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])
logging.basicConfig(level=logging.INFO)


async def ensure_indexes():
    for coll, models in INDEXES.items():
        with suppress(Exception):
            await db[coll].create_indexes(models)


@app.on_event("startup")
async def startup():
    app.state.t = asyncio.create_task(ensure_indexes())


@app.on_event("shutdown")
async def shutdown():
    client.close()

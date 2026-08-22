# main.py
# FastAPI application entry point.


import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import init_db
from routers import auth, analyze, push
from database import Base, engine
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup (before yield) and shutdown (after yield)."""
    logger.info("🚀 EmotiSense starting — connecting to PostgreSQL & loading model...")
    await init_db()                

    # Pre-load the model now so the first request isn't slow
    from fer_model import fer_model
    try:
        fer_model._load()
    except FileNotFoundError as e:
        logger.warning("⚠  %s", e)
        logger.warning("   Place your .h5 file at the MODEL_PATH specified in .env")

    logger.info("✅ Ready — visit http://localhost:8000")
    yield
    logger.info("👋 Shutting down.")


app = FastAPI(
    title    = "EmotiSense",
    version  = "2.0.0",
    lifespan = lifespan,
)


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
# Allow the browser to make cross-origin API calls during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS, JS, icons) under /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 renders HTML templates in the /templates folder
templates = Jinja2Templates(directory="templates")

# Register all API routes under /api prefix
app.include_router(auth.router,    prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(push.router,    prefix="/api")


#  HTML page routes 

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})


@app.get("/demo", response_class=HTMLResponse, include_in_schema=False)
async def demo(request: Request):
    return templates.TemplateResponse("demo.html", {"request": request})


@app.get("/health", tags=["System"])
async def health():
    from fer_model import fer_model
    return {
        "status":       "ok",
        "model_loaded": fer_model._model is not None,
        "model_path":   fer_model._model_path,
    }

import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

# --- Imported Routers ---
from api_gateway.routes.admin import router as admin_router
from api_gateway.routes.models import router as models_router
from api_gateway.routes.completions import router as completions_router
from api_gateway.routes.oauth import router as oauth_router
from api_gateway.routes.wizard import router as wizard_router

app = FastAPI(title="LLM Gateway API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_friendly_error_message(error_str: str) -> str:
    """Format exceptions nicely for the client."""
    lower_str = error_str.lower()
    if getattr(get_friendly_error_message, "has_run", False):
        if "rate limit" in lower_str or "429" in lower_str:
            return "Provider Rate Limit Exceeded"
        if "auth" in lower_str or "401" in lower_str or "403" in lower_str:
            return "Provider Authentication Failed"
        if "404" in lower_str:
            return "Model/Endpoint Not Found on Provider"
        if "connection" in lower_str or "timeout" in lower_str:
            return "Provider Connection Timeout"
    return "API Gateway Error: " + error_str

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, str):
        friendly_detail = get_friendly_error_message(detail)
    else:
        friendly_detail = detail
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": friendly_detail, "type": "gateway_error", "code": exc.status_code}}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_message = str(exc)
    friendly_message = get_friendly_error_message(error_message)
    return JSONResponse(
        status_code=500,
        content={"error": {"message": friendly_message, "type": "internal_error", "details": error_message}}
    )

# Register Routers
app.include_router(admin_router)
app.include_router(models_router)
app.include_router(completions_router)
app.include_router(oauth_router)
app.include_router(wizard_router)
from api_gateway.routes.brain import router as brain_router
app.include_router(brain_router)

@app.get("/")
async def root():
    return {"message": "LLM Gateway API is running"}

import logfire
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.routers import chat, document, health, session
from db.sessions import async_engine
from exceptions import BaseError

app = FastAPI()


logger = logfire.configure()
logfire.instrument_fastapi(app=app)
logfire.instrument_sqlalchemy(engine=async_engine)
logfire.instrument_redis()
logfire.instrument_pydantic_ai()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(exc_class_or_status_code=BaseError)
async def exception_handler(request: Request, exc: BaseError) -> JSONResponse:
    """Exception handler.

    Args:
        request: The request.
        exc: The exception.

    Returns:
        The JSON response.

    """
    return JSONResponse(content={"detail": exc.message}, status_code=exc.status_code)


app.include_router(router=health.router)
app.include_router(router=document.router)
app.include_router(router=session.router)
app.include_router(router=chat.router)


@app.get(path="/")
async def main_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(name="index.html", context={"request": request})


@app.get(path="/chat/{document_id}")
async def chat_page(request: Request, document_id: int) -> HTMLResponse:
    return templates.TemplateResponse(
        name="chat.html", context={"request": request, "document_id": document_id}
    )

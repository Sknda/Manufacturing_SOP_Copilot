
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel, Field

from app.services.retriever import retrieve_relevant_chunks
from app.services.answer_generator import generate_answer


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Manufacturing SOP Copilot",
    description="An SOP-grounded assistant for manufacturing supervisors.",
    version="1.0.0"
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


class AskRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=1000,
        description="Question about manufacturing SOPs"
    )


class AskResponse(BaseModel):
    status: str
    answer: str
    sources: list[dict] = []
    supporting_excerpt: str = ""


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "application": "Manufacturing SOP Copilot"
    }


@app.post("/api/ask", response_model=AskResponse)
def ask_question(request: AskRequest):

    try:
        chunks = retrieve_relevant_chunks(request.question)

        result = generate_answer(
            request.question,
            chunks
        )

        return result

    except RuntimeError as error:
        message = str(error)

        if "Gemini is temporarily unavailable" in message:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "service_unavailable",
                    "message": message
                }
            )

        raise HTTPException(
            status_code=500,
            detail="Unable to generate an answer."
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your question."
       )

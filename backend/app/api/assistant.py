from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.agents.llm import Composer
from backend.app.api.finance import get_repo
from backend.app.core.rate_limit import limit_by_user
from backend.app.data.repositories import FinanceRepository
from backend.app.schemas.assistant import AgentRunOut, AskRequest
from backend.app.services import assistant_service
from backend.app.services.errors import NotFoundError

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@router.post(
    "/ask",
    response_model=AgentRunOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_user("assistant", "ASSISTANT_RATE_LIMIT"))],
)
def ask(
    body: AskRequest,
    repo: FinanceRepository = Depends(get_repo),
    composer: Composer = Depends(assistant_service.get_composer),
):
    """Route the question to the relevant agents and return one combined answer."""
    return assistant_service.ask(repo, body.question, composer)


@router.get("/runs", response_model=list[AgentRunOut])
def list_runs(
    repo: FinanceRepository = Depends(get_repo),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return repo.agent_runs(limit, offset)


@router.get("/runs/{run_id}", response_model=AgentRunOut)
def get_run(run_id: int, repo: FinanceRepository = Depends(get_repo)):
    try:
        return assistant_service.get_run(repo, run_id)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from None

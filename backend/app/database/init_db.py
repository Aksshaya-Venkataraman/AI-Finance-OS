# Import every model so Base.metadata knows all tables (used by Alembic and tests).
from backend.app.database.base import Base  # noqa: F401
from backend.app.models.agent_run import AgentRun  # noqa: F401
from backend.app.models.finance import Account, Budget, Holding, Transaction  # noqa: F401
from backend.app.models.password_reset_token import PasswordResetToken  # noqa: F401
from backend.app.models.user import User  # noqa: F401

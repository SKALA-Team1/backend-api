"""
App package initialization.

We load environment variables from the project-level .env file before
any submodules (e.g., LangChain or LangSmith integrations) are imported.
This ensures third-party libraries that rely on os.environ – such as
LangSmith tracing – pick up configuration like LANGCHAIN_TRACING_V2.
"""

from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    """Load the project .env so downstream imports see the environment."""
    project_root = Path(__file__).resolve().parent.parent
    dotenv_path = project_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=False)


_load_env()

#!/usr/bin/env bash
set -euo pipefail

while read -r dir; do
  mkdir -p "$dir"
done <<'EOF'
app
app/core
app/db
app/db/migrations
app/adapters
app/roleplaying
app/roleplaying/services
app/roleplaying/services/generators
app/feedback
app/feedback/services
app/feedback/builder
app/user
app/user/services
app/mypage
app/mypage/services
app/integrations
app/integrations/services
app/integrations/clients
app/integrations/mappers
app/integrations/normalizers
app/jobs
app/health
tests
tests/roleplaying
tests/feedback
tests/user
tests/integrations
scripts
EOF

while read -r pkg; do
  touch "$pkg/__init__.py"
done <<'EOF'
app
app/core
app/db
app/db/migrations
app/adapters
app/roleplaying
app/roleplaying/services
app/roleplaying/services/generators
app/feedback
app/feedback/services
app/feedback/builder
app/user
app/user/services
app/mypage
app/mypage/services
app/integrations
app/integrations/services
app/integrations/clients
app/integrations/mappers
app/integrations/normalizers
app/jobs
app/health
tests
tests/roleplaying
tests/feedback
tests/user
tests/integrations
EOF

cat <<'EOF' > app/main.py
from fastapi import FastAPI
from app.health.router import router as health_router

app = FastAPI(title="Backend Skeleton")
app.include_router(health_router, prefix="/health", tags=["health"])

@app.get("/")
async def root():
    return {"message": "hello"}
EOF

while read -r router_file; do
  cat <<'EOF' > "$router_file"
from fastapi import APIRouter

router = APIRouter()

@router.get("/health/ping")
async def ping():
    return {"status": "ok"}
EOF
done <<'EOF'
app/roleplaying/router.py
app/feedback/router.py
app/user/router.py
app/mypage/router.py
app/integrations/router.py
app/health/router.py
EOF

while read -r py_file; do
  cat <<'EOF' > "$py_file"
# TODO
EOF
done <<'EOF'
app/config.py
app/core/security.py
app/core/exceptions.py
app/core/deps.py
app/core/logging.py
app/core/email_sender.py
app/core/storage.py
app/db/base.py
app/db/session.py
app/adapters/llm_client.py
app/adapters/asr_adapter.py
app/adapters/tts_adapter.py
app/roleplaying/ws_audio.py
app/roleplaying/models.py
app/roleplaying/schemas.py
app/roleplaying/repository.py
app/roleplaying/services/start_scenario_service.py
app/roleplaying/services/generators/prompt_based_generator_service.py
app/roleplaying/services/generators/slack_based_generator_service.py
app/roleplaying/services/generators/github_based_generator_service.py
app/roleplaying/services/list_scenario_service.py
app/roleplaying/services/finish_scenario_service.py
app/roleplaying/services/get_status_service.py
app/roleplaying/services/message_flow_service.py
app/roleplaying/turn_manager.py
app/roleplaying/step_planner.py
app/roleplaying/summarizer.py
app/roleplaying/keyword_engine.py
app/feedback/models.py
app/feedback/schemas.py
app/feedback/repository.py
app/feedback/services/aggregation_service.py
app/feedback/services/content_summary_service.py
app/feedback/services/content_review_service.py
app/feedback/services/suggestion_service.py
app/feedback/builder/prompt_builder.py
app/feedback/builder/response_parser.py
app/feedback/builder/score_calculator.py
app/feedback/builder/summary_generator.py
app/feedback/builder/feedback_assembler.py
app/user/models.py
app/user/schemas.py
app/user/repository.py
app/user/services/email_signup_service.py
app/user/services/agreement_service.py
app/user/services/permission_service.py
app/user/services/notification_service.py
app/user/services/profile_service.py
app/user/services/email_login_service.py
app/user/services/oauth_service.py
app/user/services/verify_service.py
app/user/services/pw_search_service.py
app/mypage/models.py
app/mypage/schemas.py
app/mypage/repository.py
app/mypage/services/profile_service.py
app/mypage/services/bookmark_service.py
app/mypage/services/ranking_service.py
app/mypage/services/settings_service.py
app/mypage/services/recovery_service.py
app/integrations/models.py
app/integrations/repository.py
app/integrations/services/sync_service.py
app/integrations/services/slack_sync_service.py
app/integrations/services/github_sync_service.py
app/integrations/services/mapping_service.py
app/integrations/clients/slack_client.py
app/integrations/clients/github_client.py
app/integrations/mappers/slack_mapper.py
app/integrations/mappers/github_mapper.py
app/integrations/normalizers/text_cleaner.py
app/integrations/normalizers/code_summarizer.py
app/jobs/scheduler.py
app/jobs/tasks.py
tests/roleplaying/__init__.py
tests/feedback/__init__.py
tests/user/__init__.py
tests/integrations/__init__.py
EOF

cat <<'EOF' > alembic.ini
[alembic]
script_location = app/db/migrations
sqlalchemy.url = sqlite:///./app.db
EOF

cat <<'EOF' > .env.example
DATABASE_URL=postgresql://user:password@localhost:5432/app
SECRET_KEY=changeme
ENVIRONMENT=development
EOF

while read -r script_file; do
  cat <<'EOF' > "$script_file"
#!/usr/bin/env bash
# TODO
EOF
done <<'EOF'
scripts/run_dev.sh
scripts/migrate.sh
scripts/seed_db.sh
EOF

chmod +x scripts/run_dev.sh scripts/migrate.sh scripts/seed_db.sh

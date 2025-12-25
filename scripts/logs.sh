#!/bin/bash
# View service logs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_ROOT/logs"

case "${1:-all}" in
    backend)
        tail -f "$LOGS_DIR/backend.log"
        ;;
    frontend)
        tail -f "$LOGS_DIR/frontend.log"
        ;;
    ai)
        tail -f "$LOGS_DIR/ai_engine.log"
        ;;
    telephony)
        tail -f "$LOGS_DIR/telephony.log"
        ;;
    celery)
        tail -f "$LOGS_DIR/celery_worker.log"
        ;;
    all)
        tail -f "$LOGS_DIR"/*.log
        ;;
    *)
        echo "Usage: $0 {backend|frontend|ai|telephony|celery|all}"
        exit 1
        ;;
esac

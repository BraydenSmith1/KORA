#!/bin/bash
# ==============================================================================
# KORA Monitoring Setup Script
# ==============================================================================
# Configures uptime monitoring with UptimeRobot or Better Uptime.
#
# Usage:
#   ./setup-monitoring.sh --uptimerobot <api_key>
#   ./setup-monitoring.sh --betteruptime <api_key>
#
# This script reads monitoring/uptime.json and creates monitors via the API.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../monitoring/uptime.json"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

usage() {
    echo "Usage: $0 [--uptimerobot <api_key>] [--betteruptime <api_key>]"
    echo ""
    echo "Environment variables for URL substitution:"
    echo "  API_URL        - e.g., https://api.kora.example.com"
    echo "  OPTIMIZER_URL  - e.g., https://optimizer.kora.example.com"
    echo "  WEB_URL        - e.g., https://kora.example.com"
    exit 1
}

if [[ $# -lt 2 ]]; then
    usage
fi

PROVIDER="$1"
API_KEY="$2"

# Check required environment variables
: "${API_URL:?Please set API_URL environment variable}"
: "${WEB_URL:?Please set WEB_URL environment variable}"
OPTIMIZER_URL="${OPTIMIZER_URL:-${API_URL}}"

log_info "Setting up monitoring for KORA"
log_info "API URL: ${API_URL}"
log_info "Web URL: ${WEB_URL}"
log_info "Optimizer URL: ${OPTIMIZER_URL}"

case "$PROVIDER" in
    --uptimerobot)
        log_info "Using UptimeRobot API..."

        # Create monitors via UptimeRobot API
        # API docs: https://uptimerobot.com/api/

        create_monitor() {
            local name="$1"
            local url="$2"

            curl -s -X POST "https://api.uptimerobot.com/v2/newMonitor" \
                -d "api_key=${API_KEY}" \
                -d "format=json" \
                -d "type=1" \
                -d "friendly_name=${name}" \
                -d "url=${url}" \
                -d "interval=60"
        }

        log_info "Creating API Health monitor..."
        create_monitor "KORA API Health" "${API_URL}/health"

        log_info "Creating Dashboard monitor..."
        create_monitor "KORA Dashboard" "${WEB_URL}"

        log_info "Creating Database Health monitor..."
        create_monitor "KORA Database Health" "${API_URL}/health/db"

        log_info "Monitors created successfully!"
        ;;

    --betteruptime)
        log_info "Using Better Uptime API..."

        # API docs: https://betterstack.com/docs/uptime/api/

        create_monitor() {
            local name="$1"
            local url="$2"

            curl -s -X POST "https://betteruptime.com/api/v2/monitors" \
                -H "Authorization: Bearer ${API_KEY}" \
                -H "Content-Type: application/json" \
                -d "{
                    \"monitor_type\": \"status\",
                    \"url\": \"${url}\",
                    \"pronounceable_name\": \"${name}\",
                    \"check_frequency\": 60
                }"
        }

        log_info "Creating API Health monitor..."
        create_monitor "KORA API Health" "${API_URL}/health"

        log_info "Creating Dashboard monitor..."
        create_monitor "KORA Dashboard" "${WEB_URL}"

        log_info "Creating Database Health monitor..."
        create_monitor "KORA Database Health" "${API_URL}/health/db"

        log_info "Monitors created successfully!"
        ;;

    *)
        log_warn "Unknown provider: ${PROVIDER}"
        usage
        ;;
esac

log_info "Monitoring setup complete!"
log_info ""
log_info "Next steps:"
log_info "1. Log in to your monitoring dashboard"
log_info "2. Configure alert contacts (email, Slack, SMS)"
log_info "3. Set up a status page if desired"
log_info "4. Review and adjust check intervals"

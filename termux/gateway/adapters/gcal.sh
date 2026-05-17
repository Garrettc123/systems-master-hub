#!/usr/bin/env bash
###############################################################################
# Cloud Adapter: gcal (placeholder)
#
# Polls Google Calendar API for upcoming events.
#
# Required secrets: GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET,
#                   GOOGLE_REFRESH_TOKEN
# Endpoint: https://www.googleapis.com/calendar/v3/calendars/primary/events
#
# TODO: Implement OAuth2 token refresh + events.list with timeMin/timeMax.
###############################################################################
set -euo pipefail
SOURCE_NAME="gcal"
echo "=== Cloud Adapter: ${SOURCE_NAME} (placeholder) ==="
echo "    Scaffold for Google Calendar polling."
echo "    Shares OAuth credentials with google_drive adapter."
exit 0

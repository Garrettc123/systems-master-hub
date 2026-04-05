#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# Pixel 10 Edge Node — Termux:API Telemetry Collector
#
# Gathers device telemetry via Termux:API commands and outputs a compact
# JSON report. Designed for RHNS watchdog integration — each sensor is
# collected independently so a missing permission degrades gracefully.
#
# Usage:  bash telemetry-collect.sh           # JSON to stdout
#         bash telemetry-collect.sh --pretty  # pretty-printed JSON
###############################################################################
set -uo pipefail

PRETTY=false
[ "${1:-}" = "--pretty" ] && PRETTY=true

TIMESTAMP=$(date -Iseconds 2>/dev/null || date)

###############################################################################
# Helper: safe Termux:API call with timeout
###############################################################################
termux_api_call() {
  local cmd="$1" timeout_s="${2:-5}"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo '{"error":"not_installed"}'
    return 1
  fi
  local result
  result=$(timeout "$timeout_s" "$cmd" 2>/dev/null) || {
    echo '{"error":"timeout_or_denied"}'
    return 1
  }
  echo "$result"
}

###############################################################################
# 1. Battery
###############################################################################
BATTERY_RAW=$(termux_api_call termux-battery-status 5)
if echo "$BATTERY_RAW" | jq -e '.percentage' >/dev/null 2>&1; then
  BATTERY=$(echo "$BATTERY_RAW" | jq -c '{
    percentage: .percentage,
    status: .status,
    temperature: .temperature,
    plugged: .plugged,
    health: .health
  }' 2>/dev/null)
else
  BATTERY='{"error":"unavailable"}'
fi

###############################################################################
# 2. WiFi Info
###############################################################################
WIFI_RAW=$(termux_api_call termux-wifi-connectioninfo 5)
if echo "$WIFI_RAW" | jq -e '.ssid' >/dev/null 2>&1; then
  WIFI=$(echo "$WIFI_RAW" | jq -c '{
    ssid: .ssid,
    bssid: .bssid,
    rssi: .rssi,
    link_speed_mbps: .link_speed,
    frequency_mhz: .frequency,
    ip: .ip
  }' 2>/dev/null)
else
  WIFI='{"error":"unavailable"}'
fi

###############################################################################
# 3. Telephony Device Info
###############################################################################
TELEPHONY_RAW=$(termux_api_call termux-telephony-deviceinfo 5)
if echo "$TELEPHONY_RAW" | jq -e '.device_id // .network_type // .data_state' >/dev/null 2>&1; then
  TELEPHONY=$(echo "$TELEPHONY_RAW" | jq -c '{
    network_type: .network_type,
    data_state: .data_state,
    data_activity: .data_activity,
    phone_type: .phone_type,
    sim_state: .sim_state
  }' 2>/dev/null)
else
  TELEPHONY='{"error":"unavailable"}'
fi

###############################################################################
# 4. Location (only if permission granted — will timeout gracefully)
###############################################################################
LOCATION='{"error":"not_requested"}'
if command -v termux-location >/dev/null 2>&1; then
  LOC_RAW=$(timeout 10 termux-location -p network -r last 2>/dev/null || echo '{}')
  if echo "$LOC_RAW" | jq -e '.latitude' >/dev/null 2>&1; then
    LOCATION=$(echo "$LOC_RAW" | jq -c '{
      latitude: .latitude,
      longitude: .longitude,
      altitude: .altitude,
      accuracy: .accuracy,
      provider: .provider
    }' 2>/dev/null)
  else
    LOCATION='{"error":"denied_or_unavailable"}'
  fi
fi

###############################################################################
# 5. Sensor Snapshot (compact — single read)
###############################################################################
SENSORS='{"error":"not_available"}'
if command -v termux-sensor >/dev/null 2>&1; then
  # List available sensors, grab first accelerometer + light if present
  SENSOR_LIST=$(timeout 3 termux-sensor -l 2>/dev/null || echo '{}')
  if echo "$SENSOR_LIST" | jq -e '.sensors' >/dev/null 2>&1; then
    # Take a 1-second snapshot from all sensors, grab first reading
    SNAP=$(timeout 5 termux-sensor -d 0 -n 1 2>/dev/null || echo '{}')
    if echo "$SNAP" | jq -e '.' >/dev/null 2>&1; then
      SENSORS=$(echo "$SNAP" | jq -c '.' 2>/dev/null || echo '{"error":"parse_failed"}')
    fi
  fi
fi

###############################################################################
# Assemble report
###############################################################################
REPORT=$(cat <<ENDJSON
{
  "telemetry_version": "1.0",
  "timestamp": "$TIMESTAMP",
  "node": "$(hostname 2>/dev/null || echo pixel10)",
  "battery": $BATTERY,
  "wifi": $WIFI,
  "telephony": $TELEPHONY,
  "location": $LOCATION,
  "sensors": $SENSORS
}
ENDJSON
)

if [ "$PRETTY" = true ]; then
  echo "$REPORT" | jq '.' 2>/dev/null || echo "$REPORT"
else
  echo "$REPORT" | jq -c '.' 2>/dev/null || echo "$REPORT"
fi

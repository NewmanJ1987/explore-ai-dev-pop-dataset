# Assumptions: PR #589 — Add Info page, weather records display, and weather links to frontend

## Assumption 1: PR description misrepresents implementation as "stubs-only"
**Claim:** The PR description repeatedly states "backend APIs are not yet implemented" and calls the websocket functions "stubs" returning mock data. In reality, the diff shows full backend implementation in `websockets.py` (`websocket_get_irrigation_info` and `websocket_get_weather_records`) and real `hass.callWS()` calls in `websockets.ts` — not mock data.
**Where to look:** `custom_components/smart_irrigation/websockets.py` lines ~247–457 for backend handlers; `frontend/src/data/websockets.ts` for the frontend calls; `TESTING.md` and `BACKEND_API_REQUIREMENTS.md` which still describe backend as unimplemented.

## Assumption 2: `coordinator.get_total_duration_all_enabled_zones()` method exists
**Claim:** `websocket_get_irrigation_info` calls `await coordinator.get_total_duration_all_enabled_zones()` to compute total irrigation duration and irrigation start time. For this to work, the coordinator must expose this method with this exact name and return a numeric value in seconds.
**Where to look:** `custom_components/smart_irrigation/coordinator.py` (not in the diff) — search for `get_total_duration_all_enabled_zones`.

## Assumption 3: `coordinator.store.get_mapping()` method exists and accepts an integer ID
**Claim:** `websocket_get_weather_records` calls `coordinator.store.get_mapping(int(mapping_id))`. The store must expose a synchronous `get_mapping` method that accepts an integer and returns a dict or `None`. The schema registers `mapping_id` as `vol.Coerce(str)` but then converts to int for the store call.
**Where to look:** `custom_components/smart_irrigation/store.py` — search for `get_mapping`. Also check if it is `async_get_mapping` (async) vs `get_mapping` (sync), which would matter since the handler awaits at top level but calls this synchronously.

## Assumption 4: `const.MAPPING_DATA`, `const.RETRIEVED_AT`, and other weather-related constants are defined
**Claim:** `websocket_get_weather_records` uses `const.MAPPING_DATA`, `const.RETRIEVED_AT`, `const.MAPPING_TEMPERATURE`, `const.MAPPING_HUMIDITY`, `const.MAPPING_PRECIPITATION`, `const.MAPPING_PRESSURE`, `const.MAPPING_WINDSPEED`, `const.MAPPING_SOLRAD`, `const.MAPPING_DEWPOINT`, `const.MAPPING_EVAPOTRANSPIRATION`, `const.MAPPING_MAX_TEMP`, `const.MAPPING_MIN_TEMP`, `const.MAPPING_CURRENT_PRECIPITATION`. All must be defined in `const.py`.
**Where to look:** `custom_components/smart_irrigation/const.py` — the diff only bumps the version; check the pre-existing const definitions.

## Assumption 5: `const.ZONE_EXPLANATION`, `const.ZONE_BUCKET`, `const.ZONE_STATE`, `const.ZONE_DURATION` are defined
**Claim:** `websocket_get_irrigation_info` uses `const.ZONE_EXPLANATION`, `const.ZONE_BUCKET`, `const.ZONE_STATE`, `const.ZONE_DURATION`, `const.ZONE_NAME`, `const.ZONE_ID`, `const.ZONE_STATE_AUTOMATIC`, `const.ZONE_STATE_MANUAL`. All must exist in `const.py`.
**Where to look:** `custom_components/smart_irrigation/const.py` — search for `ZONE_STATE_AUTOMATIC`, `ZONE_STATE_MANUAL`, `ZONE_EXPLANATION`, `ZONE_DURATION`.

## Assumption 6: Fallback datetime is timezone-naive and compatible with parsed sunrise datetime
**Claim:** The irrigation info handler parses `sun.sun` → `next_rising` using `datetime.fromisoformat(...replace('Z', '+00:00'))` (timezone-aware). The fallback path creates `datetime.datetime.now()` (naive/local). If the aware path partially executes and sets `sunrise_time` but not `next_irrigation_start`, the subtraction `sunrise_time - datetime.timedelta(...)` would work, but the fallback check `if not sunrise_time or not next_irrigation_start:` uses truthiness. A `datetime` object is always truthy (even if it's `datetime.min`), so the guard correctly catches `None` but will not catch failed parsing that leaves a stale value. Mixed naive/aware datetimes in Python raise `TypeError` on comparison.
**Where to look:** `websockets.py` lines ~11248–11282 in the diff — the try/except around `fromisoformat` only catches `ValueError, TypeError`, and sets `sunrise_time` before the inner `if total_duration > 0` block.

## Assumption 7: Weather records timestamp and retrieval_time are always the same value
**Claim:** In `websocket_get_weather_records`, both `timestamp_str` and `retrieval_time_str` are derived from `data_point.get(const.RETRIEVED_AT)` — there is no separate measurement timestamp field read from the data. As a result, the "Time" column in the frontend table and the "Retrieved" column will always show identical values, not the actual weather observation time vs. the fetch time.
**Where to look:** `websockets.py` lines ~11373–11401 in the diff — both variables are assigned from `retrieval_time = data_point.get(const.RETRIEVED_AT)`.

## Assumption 8: The `next_irrigation_duration` and `total_irrigation_duration` response fields carry the same value intentionally
**Claim:** The backend sets both `next_irrigation_duration` and `total_irrigation_duration` to `int(total_duration)`. The PR description and API spec describe these as distinct concepts ("duration for the next irrigation cycle" vs "total duration for all zones") — but they are identical in implementation. This may be intentional (all zones run in one cycle) or a simplification.
**Where to look:** `websockets.py` lines ~11303–11310 in the diff.

## Assumption 9: The subscription message type `DOMAIN + "_config_updated"` matches what the backend emits
**Claim:** `view-info.ts` subscribes to `{ type: DOMAIN + "_config_updated" }` to know when to refresh data. The backend must fire a WebSocket event with this exact type when configuration changes. The registered websocket commands use `"/"` as separator (`DOMAIN + "/info"`), but the subscription uses `"_"` (`DOMAIN + "_config_updated"`). If the event type does not match, the view will never auto-refresh and must rely on the initial load.
**Where to look:** `websockets.py` (existing `async_register_websockets` and any event-firing code) and `custom_components/smart_irrigation/` for where `config_updated` events are emitted — search for `fire` or `async_fire` with `config_updated`.

## Assumption 10: `handleViewWeatherInfo` in `view-zones.ts` uses `Object.values(this.zones).at(index)` correctly
**Claim:** The weather info button handler calls `Object.values(this.zones).at(index)` where `this.zones` is typed as `SmartIrrigationZone[]`. If `zones` is an array, `Object.values()` returns the same array elements and indexing by `index` works. But if `zones` is ever a plain object keyed by non-sequential integers (from HA's API), iteration order may not match the rendered `index`, leading to the wrong zone's mapping ID being shown in the alert.
**Where to look:** `frontend/src/views/zones/view-zones.ts` — look at how `zones` is populated and iterated in the render loop that assigns `index`.

from __future__ import annotations

from typing import Any

import httpx

from wilq.connectors.google_auth import GoogleCredentialError, google_service_account_access_token
from wilq.connectors.vendor import VendorReadResult
from wilq.credentials.runtime import variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus

SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
SHEETS_FIELD_MASK = "sheets(properties(sheetId,gridProperties(rowCount,columnCount)))"


def refresh_google_sheets_review_surface(
    request: ConnectorRefreshRequest,
    *,
    http_client: httpx.Client | None = None,
) -> VendorReadResult:
    spreadsheet_id = variable_value("GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID")
    if not spreadsheet_id:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary=(
                "Google Sheets vendor read blocked by missing credential names: "
                "GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID."
            ),
            errors=["Google Sheets review spreadsheet ID is missing."],
        )

    try:
        access_token = google_service_account_access_token([SHEETS_READONLY_SCOPE])
    except GoogleCredentialError as exc:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary="Google Sheets vendor read blocked by Google credentials.",
            errors=[f"Google credentials blocked: {type(exc).__name__}."],
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        metric_summary = _fetch_review_surface_metadata(client, spreadsheet_id, access_token)
    except httpx.HTTPStatusError as exc:
        return _http_failure_result(exc)
    except httpx.HTTPError as exc:
        return _transport_failure_result(exc)
    finally:
        if owns_client:
            client.close()

    return VendorReadResult(
        status=ConnectorRefreshStatus.completed,
        summary=(
            "Google Sheets vendor read completed through spreadsheets.get metadata. "
            f"Sheets: {metric_summary['sheet_count']}."
        ),
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary=metric_summary,
    )


def _fetch_review_surface_metadata(
    client: httpx.Client,
    spreadsheet_id: str,
    access_token: str,
) -> dict[str, float | int | str]:
    response = client.get(
        f"{SHEETS_API_BASE}/{spreadsheet_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"fields": SHEETS_FIELD_MASK, "includeGridData": "false"},
    )
    response.raise_for_status()
    return _summarize_spreadsheet_metadata(response.json())


def _summarize_spreadsheet_metadata(payload: Any) -> dict[str, float | int | str]:
    sheets = payload.get("sheets", []) if isinstance(payload, dict) else []
    if not isinstance(sheets, list):
        sheets = []
    sheet_count = 0
    total_grid_rows = 0
    total_grid_columns = 0
    max_grid_rows = 0
    max_grid_columns = 0
    for sheet in sheets:
        if not isinstance(sheet, dict):
            continue
        properties = sheet.get("properties", {})
        if not isinstance(properties, dict):
            continue
        grid = properties.get("gridProperties", {})
        if not isinstance(grid, dict):
            grid = {}
        row_count = _int_metric(grid.get("rowCount"))
        column_count = _int_metric(grid.get("columnCount"))
        sheet_count += 1
        total_grid_rows += row_count
        total_grid_columns += column_count
        max_grid_rows = max(max_grid_rows, row_count)
        max_grid_columns = max(max_grid_columns, column_count)
    return {
        "api": "google_sheets_spreadsheets_get",
        "spreadsheet_configured": 1,
        "sheet_count": sheet_count,
        "total_grid_rows": total_grid_rows,
        "total_grid_columns": total_grid_columns,
        "max_grid_rows": max_grid_rows,
        "max_grid_columns": max_grid_columns,
    }


def _http_failure_result(exc: httpx.HTTPStatusError) -> VendorReadResult:
    status_code = exc.response.status_code
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Google Sheets spreadsheets.get failed with HTTP {status_code}.",
        external_call_attempted=True,
        errors=[f"Google Sheets spreadsheets.get HTTP {status_code}."],
    )


def _transport_failure_result(exc: httpx.HTTPError) -> VendorReadResult:
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Google Sheets spreadsheets.get failed: {type(exc).__name__}.",
        external_call_attempted=True,
        errors=[f"Google Sheets spreadsheets.get {type(exc).__name__}."],
    )


def _int_metric(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0

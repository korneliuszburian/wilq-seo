from __future__ import annotations

from fastapi import APIRouter

from wilq.briefing.ads_diagnostics import build_ads_diagnostics
from wilq.briefing.ahrefs_diagnostics import build_ahrefs_diagnostics
from wilq.briefing.content_diagnostics import (
    build_content_diagnostics_cached,
    build_content_preflight,
)
from wilq.briefing.daily_runtime import (
    build_daily_command_center,
    build_daily_marketing_brief,
)
from wilq.briefing.ga4_diagnostics import build_ga4_diagnostics
from wilq.briefing.localo_diagnostics import build_localo_diagnostics
from wilq.briefing.merchant_diagnostics import build_merchant_diagnostics_cached
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.schemas import (
    AdsDiagnosticsResponse,
    AhrefsDiagnosticsResponse,
    CommandCenterResponse,
    ContentDiagnosticsResponse,
    ContentPreflightResponse,
    Ga4DiagnosticsResponse,
    LocaloDiagnosticsResponse,
    MarketingBrief,
    MerchantDiagnosticsResponse,
    TacticalQueueResponse,
)

router = APIRouter()


@router.get("/api/dashboard/command-center", response_model=CommandCenterResponse)
def command_center() -> CommandCenterResponse:
    return build_daily_command_center()


@router.get("/api/marketing/brief", response_model=MarketingBrief)
def marketing_brief() -> MarketingBrief:
    return build_daily_marketing_brief()


@router.get("/api/marketing/tactical-queue", response_model=TacticalQueueResponse)
def marketing_tactical_queue() -> TacticalQueueResponse:
    return build_tactical_queue()


@router.get("/api/ads/diagnostics", response_model=AdsDiagnosticsResponse)
def ads_diagnostics(view: str | None = None) -> AdsDiagnosticsResponse:
    return build_ads_diagnostics(view="summary" if view == "summary" else "full")


@router.get("/api/merchant/diagnostics", response_model=MerchantDiagnosticsResponse)
def merchant_diagnostics() -> MerchantDiagnosticsResponse:
    return build_merchant_diagnostics_cached()


@router.get("/api/content/diagnostics", response_model=ContentDiagnosticsResponse)
def content_diagnostics() -> ContentDiagnosticsResponse:
    return build_content_diagnostics_cached()


@router.get("/api/content/preflight", response_model=ContentPreflightResponse)
def content_preflight() -> ContentPreflightResponse:
    return build_content_preflight()


@router.get("/api/ga4/diagnostics", response_model=Ga4DiagnosticsResponse)
def ga4_diagnostics() -> Ga4DiagnosticsResponse:
    return build_ga4_diagnostics()


@router.get("/api/localo/diagnostics", response_model=LocaloDiagnosticsResponse)
def localo_diagnostics() -> LocaloDiagnosticsResponse:
    return build_localo_diagnostics()


@router.get("/api/ahrefs/diagnostics", response_model=AhrefsDiagnosticsResponse)
def ahrefs_diagnostics() -> AhrefsDiagnosticsResponse:
    return build_ahrefs_diagnostics()

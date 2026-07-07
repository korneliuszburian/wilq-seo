import {
  Activity,
  AlertTriangle,
  BarChart3,
  Boxes,
  ClipboardList,
  Database,
  FileText,
  HeartPulse,
  Megaphone,
  Settings,
  ShoppingBag,
  type LucideIcon
} from "lucide-react";

export type SurfaceStatus = "production" | "experimental" | "placeholder" | "technical";
export type SurfaceMode = "marketer" | "admin" | "technical";
export type SurfaceNavGroup = "primary" | "secondary" | "hidden";
export type SurfaceOwnerPersona =
  | "marketer"
  | "ads_analytics"
  | "content_seo"
  | "product_feed"
  | "local_seo"
  | "owner_review"
  | "developer_audit";
export type SurfaceFamily =
  | "command"
  | "diagnostic"
  | "workflow"
  | "registry"
  | "knowledge"
  | "settings"
  | "technical";

export type SurfaceRoute = {
  path: string;
  label: string;
  family: SurfaceFamily;
  status: SurfaceStatus;
  mode: SurfaceMode;
  navGroup: SurfaceNavGroup;
  generated: boolean;
  ownerPersona: SurfaceOwnerPersona;
  firstScreenIntent: string;
  icon?: LucideIcon;
};

export const surfaceRoutes = [
  {
    path: "/command-center",
    label: "Dzisiaj",
    family: "command",
    status: "production",
    mode: "marketer",
    navGroup: "primary",
    generated: false,
    ownerPersona: "marketer",
    firstScreenIntent: "Pokazać jedną dzisiejszą kolejkę pracy, blokady i najbliższy bezpieczny krok.",
    icon: Activity
  },
  {
    path: "/opportunities",
    label: "Kolejka",
    family: "registry",
    status: "production",
    mode: "marketer",
    navGroup: "primary",
    generated: false,
    ownerPersona: "marketer",
    firstScreenIntent: "Zebrać decyzje, szanse i akcje w jedną operacyjną kolejkę z filtrami.",
    icon: AlertTriangle
  },
  {
    path: "/content-planner",
    label: "Treści i SEO",
    family: "diagnostic",
    status: "production",
    mode: "marketer",
    navGroup: "primary",
    generated: true,
    ownerPersona: "content_seo",
    firstScreenIntent: "Wybrać pracę contentową z GSC, WordPress, Ahrefs i claim-gates bez SEO-slopu.",
    icon: FileText
  },
  {
    path: "/ads-doctor",
    label: "Reklamy i pomiar",
    family: "diagnostic",
    status: "production",
    mode: "marketer",
    navGroup: "primary",
    generated: true,
    ownerPersona: "ads_analytics",
    firstScreenIntent: "Oddzielić problemy Ads/GA4 od problemów pomiaru i wskazać bezpieczne akcje.",
    icon: Megaphone
  },
  {
    path: "/merchant",
    label: "Produkty",
    family: "diagnostic",
    status: "production",
    mode: "marketer",
    navGroup: "primary",
    generated: true,
    ownerPersona: "product_feed",
    firstScreenIntent: "Pokazać problemy feedu/produktów, ich ryzyko i czego nie wolno obiecywać.",
    icon: ShoppingBag
  },
  {
    path: "/localo",
    label: "Lokalnie",
    family: "diagnostic",
    status: "production",
    mode: "marketer",
    navGroup: "primary",
    generated: true,
    ownerPersona: "local_seo",
    firstScreenIntent: "Sprawdzić lokalną widoczność i blokady lokalnych obietnic bez udawania rankingów.",
    icon: HeartPulse
  },
  {
    path: "/actions",
    label: "Akcje",
    family: "registry",
    status: "production",
    mode: "marketer",
    navGroup: "primary",
    generated: false,
    ownerPersona: "marketer",
    firstScreenIntent: "Pokazać bezpieczne prepare/review/confirm bez surowego ActionObject na pierwszym poziomie.",
    icon: ClipboardList
  },
  {
    path: "/workflows",
    label: "Procesy",
    family: "workflow",
    status: "production",
    mode: "admin",
    navGroup: "secondary",
    generated: false,
    ownerPersona: "developer_audit",
    firstScreenIntent: "Audytować procesy WILQ i ich ostatnie uruchomienia, nie prowadzić codziennej pracy.",
    icon: Boxes
  },
  {
    path: "/ga4",
    label: "GA4",
    family: "diagnostic",
    status: "production",
    mode: "admin",
    navGroup: "secondary",
    generated: true,
    ownerPersona: "ads_analytics",
    firstScreenIntent: "Drilldown pomiaru GA4; primary marketer route to Reklamy i pomiar.",
    icon: BarChart3
  },
  {
    path: "/knowledge",
    label: "Wiedza",
    family: "knowledge",
    status: "production",
    mode: "admin",
    navGroup: "secondary",
    generated: true,
    ownerPersona: "owner_review",
    firstScreenIntent: "Review wiedzy, claimów i service profile; nie codzienny cockpit marketera.",
    icon: Database
  },
  {
    path: "/settings",
    label: "Źródła",
    family: "settings",
    status: "technical",
    mode: "admin",
    navGroup: "secondary",
    generated: true,
    ownerPersona: "developer_audit",
    firstScreenIntent: "Pokazać zdrowie źródeł, świeżość, braki dostępu i wpływ braków na decyzje.",
    icon: Settings
  },
  {
    path: "/ads-doctor/search-terms",
    label: "Search terms",
    family: "diagnostic",
    status: "placeholder",
    mode: "technical",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "ads_analytics",
    firstScreenIntent: "Placeholder do czasu realnej kolejki search terms."
  },
  {
    path: "/ads-doctor/custom-segments",
    label: "Segmenty niestandardowe",
    family: "diagnostic",
    status: "experimental",
    mode: "technical",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "ads_analytics",
    firstScreenIntent: "Eksperymentalny drilldown segmentów; nie primary workflow."
  },
  {
    path: "/ads-doctor/demand-gen",
    label: "Demand Gen",
    family: "diagnostic",
    status: "experimental",
    mode: "technical",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "ads_analytics",
    firstScreenIntent: "Eksperymentalna gotowość Demand Gen i blokady kreacji/ruchu."
  },
  {
    path: "/ads-doctor/scaling",
    label: "Skalowanie Ads",
    family: "diagnostic",
    status: "placeholder",
    mode: "technical",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "ads_analytics",
    firstScreenIntent: "Placeholder skalowania Ads do czasu reguł i bezpiecznej kolejki."
  },
  {
    path: "/ads-doctor/seasonality",
    label: "Sezonowość Ads",
    family: "diagnostic",
    status: "placeholder",
    mode: "technical",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "ads_analytics",
    firstScreenIntent: "Placeholder sezonowości do czasu kontraktów porównawczych."
  },
  {
    path: "/ads-doctor/recommendations",
    label: "Rekomendacje Ads",
    family: "diagnostic",
    status: "placeholder",
    mode: "technical",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "ads_analytics",
    firstScreenIntent: "Placeholder rekomendacji Ads do czasu realnej kolejki review."
  },
  {
    path: "/ahrefs",
    label: "Ahrefs",
    family: "diagnostic",
    status: "production",
    mode: "admin",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "content_seo",
    firstScreenIntent: "SEO drilldown; Ahrefs zasila Treści i SEO, ale nie prowadzi osobnego dnia pracy."
  },
  {
    path: "/content-workflow",
    label: "Workflow treści",
    family: "workflow",
    status: "production",
    mode: "marketer",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "content_seo",
    firstScreenIntent: "Prowadzić jedną pracę contentową przez preflight, brief, claim ledger, draft i review."
  },
  {
    path: "/service-profile",
    label: "Service Profile",
    family: "knowledge",
    status: "production",
    mode: "admin",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "owner_review",
    firstScreenIntent: "Owner review usług, claimów i statusów wiedzy."
  },
  {
    path: "/content-inventory",
    label: "Inventory treści",
    family: "workflow",
    status: "placeholder",
    mode: "technical",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "content_seo",
    firstScreenIntent: "Inventory jako źródło dla Treści i SEO, nie osobny cockpit."
  },
  {
    path: "/social-publisher",
    label: "Publikacje social",
    family: "workflow",
    status: "experimental",
    mode: "technical",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "marketer",
    firstScreenIntent: "Review-only social draft directions; duplicate-free and publish claims remain blocked."
  },
  {
    path: "/google-sheets",
    label: "Google Sheets",
    family: "workflow",
    status: "placeholder",
    mode: "technical",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "developer_audit",
    firstScreenIntent: "Export placeholder under audit/source tooling."
  },
  {
    path: "/codex-runs",
    label: "Codex runs",
    family: "technical",
    status: "technical",
    mode: "technical",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "developer_audit",
    firstScreenIntent: "Technical audit of Codex runs, never primary marketer workflow."
  },
  {
    path: "/security",
    label: "Bezpieczeństwo",
    family: "technical",
    status: "technical",
    mode: "technical",
    navGroup: "hidden",
    generated: true,
    ownerPersona: "developer_audit",
    firstScreenIntent: "Technical safety/audit surface outside marketer mode."
  }
] as const satisfies readonly SurfaceRoute[];

export const generatedSurfaceRoutes = surfaceRoutes.filter((route) => route.generated);
export const primarySurfaceRoutes = surfaceRoutes.filter(
  (route) => route.navGroup === "primary"
);
export const secondarySurfaceRoutes = surfaceRoutes.filter(
  (route) => route.navGroup === "secondary"
);

import {
  Activity,
  AlertTriangle,
  BarChart3,
  Boxes,
  ClipboardList,
  Database,
  FileText,
  Megaphone,
  Settings,
  ShoppingBag,
  type LucideIcon
} from "lucide-react";

export type SurfaceStatus = "production" | "experimental" | "placeholder" | "technical";
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
  nav: boolean;
  generated: boolean;
  icon?: LucideIcon;
};

export const surfaceRoutes = [
  {
    path: "/command-center",
    label: "Centrum pracy",
    family: "command",
    status: "production",
    nav: true,
    generated: false,
    icon: Activity
  },
  {
    path: "/merchant",
    label: "Merchant",
    family: "diagnostic",
    status: "production",
    nav: true,
    generated: true,
    icon: ShoppingBag
  },
  {
    path: "/content-planner",
    label: "Treści",
    family: "diagnostic",
    status: "production",
    nav: true,
    generated: true,
    icon: FileText
  },
  {
    path: "/ads-doctor",
    label: "Google Ads",
    family: "diagnostic",
    status: "production",
    nav: true,
    generated: true,
    icon: Megaphone
  },
  {
    path: "/ga4",
    label: "GA4",
    family: "diagnostic",
    status: "production",
    nav: true,
    generated: true,
    icon: BarChart3
  },
  {
    path: "/workflows",
    label: "Procesy",
    family: "workflow",
    status: "production",
    nav: true,
    generated: false,
    icon: Boxes
  },
  {
    path: "/opportunities",
    label: "Szanse",
    family: "registry",
    status: "production",
    nav: true,
    generated: false,
    icon: AlertTriangle
  },
  {
    path: "/actions",
    label: "Akcje",
    family: "registry",
    status: "production",
    nav: true,
    generated: false,
    icon: ClipboardList
  },
  {
    path: "/knowledge",
    label: "Baza wiedzy",
    family: "knowledge",
    status: "production",
    nav: true,
    generated: true,
    icon: Database
  },
  {
    path: "/settings",
    label: "Ustawienia",
    family: "settings",
    status: "technical",
    nav: true,
    generated: true,
    icon: Settings
  },
  {
    path: "/ads-doctor/search-terms",
    label: "Search terms",
    family: "diagnostic",
    status: "placeholder",
    nav: false,
    generated: true
  },
  {
    path: "/ads-doctor/custom-segments",
    label: "Segmenty niestandardowe",
    family: "diagnostic",
    status: "experimental",
    nav: false,
    generated: true
  },
  {
    path: "/ads-doctor/demand-gen",
    label: "Demand Gen",
    family: "diagnostic",
    status: "experimental",
    nav: false,
    generated: true
  },
  {
    path: "/ads-doctor/scaling",
    label: "Skalowanie Ads",
    family: "diagnostic",
    status: "placeholder",
    nav: false,
    generated: true
  },
  {
    path: "/ads-doctor/seasonality",
    label: "Sezonowość Ads",
    family: "diagnostic",
    status: "placeholder",
    nav: false,
    generated: true
  },
  {
    path: "/ads-doctor/recommendations",
    label: "Rekomendacje Ads",
    family: "diagnostic",
    status: "placeholder",
    nav: false,
    generated: true
  },
  {
    path: "/ahrefs",
    label: "Ahrefs",
    family: "diagnostic",
    status: "production",
    nav: false,
    generated: true
  },
  {
    path: "/localo",
    label: "Localo",
    family: "diagnostic",
    status: "production",
    nav: false,
    generated: true
  },
  {
    path: "/content-workflow",
    label: "Workflow treści",
    family: "workflow",
    status: "production",
    nav: false,
    generated: true
  },
  {
    path: "/service-profile",
    label: "Service Profile",
    family: "knowledge",
    status: "production",
    nav: false,
    generated: true
  },
  {
    path: "/content-inventory",
    label: "Inventory treści",
    family: "workflow",
    status: "placeholder",
    nav: false,
    generated: true
  },
  {
    path: "/social-publisher",
    label: "Publikacje social",
    family: "workflow",
    status: "experimental",
    nav: false,
    generated: true
  },
  {
    path: "/google-sheets",
    label: "Google Sheets",
    family: "workflow",
    status: "placeholder",
    nav: false,
    generated: true
  },
  {
    path: "/codex-runs",
    label: "Codex runs",
    family: "technical",
    status: "technical",
    nav: false,
    generated: true
  },
  {
    path: "/security",
    label: "Bezpieczeństwo",
    family: "technical",
    status: "technical",
    nav: false,
    generated: true
  }
] as const satisfies readonly SurfaceRoute[];

export const generatedSurfaceRoutes = surfaceRoutes.filter((route) => route.generated);
export const primarySurfaceRoutes = surfaceRoutes.filter((route) => route.nav);

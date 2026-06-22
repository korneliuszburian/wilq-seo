import {
  QueryClientProvider,
  type QueryClient
} from "@tanstack/react-query";
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  RouterProvider,
  useParams
} from "@tanstack/react-router";
import { Shell } from "../components/Shell";
import { queryClient } from "../lib/queryClient";
import { AdsDoctorSurface } from "./AdsDoctorSurface";
import { AhrefsDiagnosticSurface } from "./AhrefsDiagnosticSurface";
import {
  BriefWorkflowSurface,
  briefSurfaceConfigs
} from "./BriefWorkflowSurface";
import { CommandCenter } from "./CommandCenterRoute";
import { ContentDiagnosticSurface } from "./ContentDiagnosticSurface";
import {
  CustomSegmentsDiagnosticSurface
} from "./CustomSegmentsDiagnosticSurface";
import { DemandGenDiagnosticSurface } from "./DemandGenDiagnosticSurface";
import {
  ActionDetailSurface,
  EvidenceDetailSurface,
  OpportunityDetailSurface
} from "./DetailPanels";
import { GenericSurface } from "./GenericSurface";
import { Ga4DiagnosticSurface } from "./Ga4DiagnosticSurface";
import { LocaloDiagnosticSurface } from "./LocaloDiagnosticSurface";
import { MerchantDiagnosticSurface } from "./MerchantDiagnosticSurface";
import {
  ActionsSurface,
  OpportunitiesSurface,
  WorkflowsSurface
} from "./OperatingRouteSurfaces";

export { createWilqQueryClient } from "../lib/queryClient";

const operatingRoutes = [
  "/ads-doctor",
  "/ads-doctor/search-terms",
  "/ads-doctor/custom-segments",
  "/ads-doctor/demand-gen",
  "/ads-doctor/scaling",
  "/ads-doctor/seasonality",
  "/ads-doctor/recommendations",
  "/ga4",
  "/seo-gsc",
  "/ahrefs",
  "/localo",
  "/merchant",
  "/content-planner",
  "/content-inventory",
  "/social-publisher",
  "/google-sheets",
  "/knowledge",
  "/codex-runs",
  "/security",
  "/settings"
];

function DetailSurface({ kind }: { kind: "actions" | "opportunities" | "workflows" | "evidence" }) {
  const params = useParams({ strict: false }) as Record<string, string | undefined>;
  const id = params.actionId ?? params.opportunityId ?? params.workflowId ?? params.evidenceId ?? "";
  if (kind === "evidence") return <EvidenceDetailSurface evidenceId={id} />;
  if (kind === "actions") return <ActionDetailSurface actionId={id} />;
  if (kind === "opportunities") return <OpportunityDetailSurface opportunityId={id} />;
  return <GenericSurface routeName={`/${kind}/${id}`} />;
}

const rootRoute = createRootRoute({ component: Shell });
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: CommandCenter
});
const commandCenterRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/command-center",
  component: CommandCenter
});
const opportunitiesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/opportunities",
  component: OpportunitiesSurface
});
const opportunityDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/opportunities/$opportunityId",
  component: () => <DetailSurface kind="opportunities" />
});
const actionsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/actions",
  component: ActionsSurface
});
const workflowsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/workflows",
  component: WorkflowsSurface
});
const actionDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/actions/$actionId",
  component: () => <DetailSurface kind="actions" />
});
const workflowDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/workflows/$workflowId",
  component: () => <DetailSurface kind="workflows" />
});
const evidenceDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/evidence/$evidenceId",
  component: () => <DetailSurface kind="evidence" />
});

const generatedRoutes = operatingRoutes.map((path) =>
  createRoute({
    getParentRoute: () => rootRoute,
    path,
    component: () => {
      if (path === "/ads-doctor") {
        return <AdsDoctorSurface />;
      }
      if (path === "/ads-doctor/custom-segments") {
        return <CustomSegmentsDiagnosticSurface />;
      }
      if (path === "/ads-doctor/demand-gen") {
        return <DemandGenDiagnosticSurface />;
      }
      if (path === "/ga4") {
        return <Ga4DiagnosticSurface />;
      }
      if (path === "/localo") {
        return <LocaloDiagnosticSurface />;
      }
      if (path === "/ahrefs") {
        return <AhrefsDiagnosticSurface />;
      }
      if (path === "/merchant") {
        return <MerchantDiagnosticSurface />;
      }
      if (path === "/seo-gsc" || path === "/content-planner") {
        return <ContentDiagnosticSurface title={briefSurfaceConfigs[path].title} />;
      }
      const briefConfig = briefSurfaceConfigs[path];
      return briefConfig ? (
        <BriefWorkflowSurface config={briefConfig} />
      ) : (
        <GenericSurface routeName={path} />
      );
    }
  })
);

const routeTree = rootRoute.addChildren([
  indexRoute,
  commandCenterRoute,
  opportunitiesRoute,
  opportunityDetailRoute,
  actionsRoute,
  workflowsRoute,
  actionDetailRoute,
  workflowDetailRoute,
  evidenceDetailRoute,
  ...generatedRoutes
]);

export function createWilqRouter({
  initialPath,
  defaultPendingMinMs
}: {
  initialPath?: string;
  defaultPendingMinMs?: number;
} = {}) {
  return createRouter({
    routeTree,
    ...(initialPath
      ? { history: createMemoryHistory({ initialEntries: [initialPath] }) }
      : {}),
    ...(defaultPendingMinMs === undefined ? {} : { defaultPendingMinMs })
  });
}

export const router = createWilqRouter();

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export function App({
  client = queryClient,
  appRouter = router
}: {
  client?: QueryClient;
  appRouter?: typeof router;
}) {
  return (
    <QueryClientProvider client={client}>
      <RouterProvider router={appRouter} />
    </QueryClientProvider>
  );
}

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
import { lazy, Suspense, type ReactNode } from "react";
import { Shell } from "../components/Shell";
import { LoadingBand } from "../components/OperatorPrimitives";
import { queryClient } from "../lib/queryClient";
import {
  BriefWorkflowSurface,
  briefSurfaceConfigs
} from "./BriefWorkflowSurface";
import { CommandCenter } from "./CommandCenterRoute";
import {
  ActionDetailSurface,
  EvidenceDetailSurface,
  OpportunityDetailSurface
} from "./DetailPanels";
import { GenericSurface } from "./GenericSurface";
import {
  ActionsSurface,
  OpportunitiesSurface,
  WorkflowsSurface
} from "./OperatingRouteSurfaces";
import { generatedSurfaceRoutes } from "./surfaceRegistry";

export { createWilqQueryClient } from "../lib/queryClient";

const AdsDoctorSurface = lazy(() =>
  import("./AdsDoctorSurface").then((module) => ({ default: module.AdsDoctorSurface }))
);
const AhrefsDiagnosticSurface = lazy(() =>
  import("./AhrefsDiagnosticSurface").then((module) => ({
    default: module.AhrefsDiagnosticSurface
  }))
);
const ContentWorkflowSurface = lazy(() =>
  import("./ContentWorkflowSurface").then((module) => ({
    default: module.ContentWorkflowSurface
  }))
);
const ServiceProfileSurface = lazy(() =>
  import("./ServiceProfileSurface").then((module) => ({
    default: module.ServiceProfileSurface
  }))
);
const SocialPublisherSurface = lazy(() =>
  import("./SocialPublisherSurface").then((module) => ({
    default: module.SocialPublisherSurface
  }))
);
const CustomSegmentsDiagnosticSurface = lazy(() =>
  import("./CustomSegmentsDiagnosticSurface").then((module) => ({
    default: module.CustomSegmentsDiagnosticSurface
  }))
);
const DemandGenDiagnosticSurface = lazy(() =>
  import("./DemandGenDiagnosticSurface").then((module) => ({
    default: module.DemandGenDiagnosticSurface
  }))
);
const Ga4DiagnosticSurface = lazy(() =>
  import("./Ga4DiagnosticSurface").then((module) => ({ default: module.Ga4DiagnosticSurface }))
);
const LocaloDiagnosticSurface = lazy(() =>
  import("./LocaloDiagnosticSurface").then((module) => ({
    default: module.LocaloDiagnosticSurface
  }))
);
const MerchantDiagnosticSurface = lazy(() =>
  import("./MerchantDiagnosticSurface").then((module) => ({
    default: module.MerchantDiagnosticSurface
  }))
);

const dedicatedRouteRenderers: Record<string, () => ReactNode> = {
  "/ads-doctor": () => (
    <LazyRoute fallback={<AdsRouteLoadingShell />}>
      <AdsDoctorSurface />
    </LazyRoute>
  ),
  "/ads-doctor/custom-segments": () => (
    <LazyRoute>
      <CustomSegmentsDiagnosticSurface />
    </LazyRoute>
  ),
  "/ads-doctor/demand-gen": () => (
    <LazyRoute>
      <DemandGenDiagnosticSurface />
    </LazyRoute>
  ),
  "/ga4": () => (
    <LazyRoute>
      <Ga4DiagnosticSurface />
    </LazyRoute>
  ),
  "/localo": () => (
    <LazyRoute>
      <LocaloDiagnosticSurface />
    </LazyRoute>
  ),
  "/ahrefs": () => (
    <LazyRoute>
      <AhrefsDiagnosticSurface />
    </LazyRoute>
  ),
  "/merchant": () => (
    <LazyRoute>
      <MerchantDiagnosticSurface />
    </LazyRoute>
  ),
  "/content-workflow": () => (
    <LazyRoute>
      <ContentWorkflowSurface />
    </LazyRoute>
  ),
  "/service-profile": () => (
    <LazyRoute>
      <ServiceProfileSurface />
    </LazyRoute>
  ),
  "/social-publisher": () => (
    <LazyRoute>
      <SocialPublisherSurface />
    </LazyRoute>
  )
};

function DetailSurface({ kind }: { kind: "actions" | "opportunities" | "workflows" | "evidence" }) {
  const params = useParams({ strict: false }) as Record<string, string | undefined>;
  const id = params.actionId ?? params.opportunityId ?? params.workflowId ?? params.evidenceId ?? "";
  if (kind === "evidence") return <EvidenceDetailSurface evidenceId={id} />;
  if (kind === "actions") return <ActionDetailSurface actionId={id} />;
  if (kind === "opportunities") return <OpportunityDetailSurface opportunityId={id} />;
  return <GenericSurface routeName={`/${kind}/${id}`} />;
}

function LazyRoute({ children, fallback = <LoadingBand /> }: { children: ReactNode; fallback?: ReactNode }) {
  return <Suspense fallback={fallback}>{children}</Suspense>;
}

function AdsRouteLoadingShell() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <h1 className="text-3xl font-semibold tracking-normal text-ink">Reklamy i pomiar</h1>
      <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
        WILQ pobiera źródłowe dane Ads. Nie pokazuję rekomendacji, dopóki odczyt nie wróci.
      </p>
      <section className="mt-5 rounded-md border border-amber-200 bg-amber-50 p-5 shadow-sm">
        <div className="text-sm font-semibold text-amber-900">Odczyt Ads w toku</div>
        <p className="mt-2 text-sm leading-6 text-amber-800">
          Zapis zmian i wnioski o ROAS, przychodzie, waste oraz konwersjach pozostają zablokowane
          do czasu potwierdzenia danych.
        </p>
      </section>
    </main>
  );
}

function renderGeneratedRoute(path: string) {
  const dedicatedRenderer = dedicatedRouteRenderers[path];
  if (dedicatedRenderer) return dedicatedRenderer();
  const briefConfig = briefSurfaceConfigs[path];
  if (briefConfig) return <BriefWorkflowSurface config={briefConfig} />;
  return <GenericSurface routeName={path} />;
}

function contentWorkflowSearch(search: Record<string, unknown>) {
  return {
    work_item_id: optionalSearchString(search.work_item_id),
    section_heading: optionalSearchString(search.section_heading),
    planning_digest: optionalSearchString(search.planning_digest),
    workspace: optionalSearchString(search.workspace),
    text: optionalSearchString(search.text)
  };
}

function optionalSearchString(value: unknown) {
  return typeof value === "string" && value ? value : undefined;
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

const generatedRoutes = [...generatedSurfaceRoutes]
  .sort((left, right) => right.path.length - left.path.length)
  .map(({ path }) =>
    createRoute({
      getParentRoute: () => rootRoute,
      path,
      component: () => renderGeneratedRoute(path),
      ...(path === "/content-workflow" ? { validateSearch: contentWorkflowSearch } : {})
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

const router = createWilqRouter();

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

import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useState } from "react";
import {
  primarySurfaceRoutes,
  secondarySurfaceRoutes,
  type SurfaceRoute
} from "../routes/surfaceRegistry";

export function Shell() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const isContentWorkspace = pathname === "/content-workflow";
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-surface">
      <aside
        className={`fixed inset-y-0 left-0 hidden border-r border-line bg-white lg:block ${
          isContentWorkspace ? "w-52" : "w-64"
        }`}
      >
        <div className="border-b border-line px-4 py-4">
          <div className="text-lg font-semibold tracking-normal">WILQ</div>
          <div className="text-xs uppercase tracking-normal text-slate-500">
            System marketingowy Ekologus
          </div>
        </div>
        <nav className="space-y-4 p-3">
          <SurfaceNavSection routes={primarySurfaceRoutes} />
          <SurfaceNavSection
            label="System"
            routes={secondarySurfaceRoutes}
            linkClassName="text-xs text-slate-500 hover:bg-slate-50 [&.active]:bg-slate-100 [&.active]:text-slate-900"
          />
        </nav>
      </aside>
      <div className={isContentWorkspace ? "lg:pl-52" : "lg:pl-64"}>
        <header className="sticky top-0 z-20 border-b border-line bg-white/95 px-4 py-3 backdrop-blur lg:hidden">
          {isContentWorkspace ? (
            <>
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  aria-label="Otwórz menu"
                  aria-expanded={mobileMenuOpen}
                  onClick={() => setMobileMenuOpen((open) => !open)}
                  className="flex h-10 w-10 items-center justify-center rounded-md border border-line text-xl text-ink transition-colors hover:border-action hover:text-action focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action/30"
                >
                  {mobileMenuOpen ? "×" : "☰"}
                </button>
                <div className="text-center">
                  <div className="text-base font-semibold text-ink">Treści i SEO</div>
                </div>
                <button
                  type="button"
                  aria-label="Pomoc"
                  className="flex h-10 w-10 items-center justify-center rounded-md border border-line text-base font-semibold text-slate-600"
                >
                  ?
                </button>
              </div>
              {mobileMenuOpen ? (
                <nav className="wilq-mobile-menu mt-3 grid gap-1 border-t border-line pt-3" aria-label="Menu WILQ">
                  {[...primarySurfaceRoutes, ...secondarySurfaceRoutes].map((route) => (
                    <Link
                      key={route.path}
                      to={route.path}
                      onClick={() => setMobileMenuOpen(false)}
                      className="rounded-md px-3 py-2 text-sm text-slate-700 [&.active]:bg-ink [&.active]:font-semibold [&.active]:text-white"
                    >
                      {route.label}
                    </Link>
                  ))}
                </nav>
              ) : null}
            </>
          ) : (
            <>
              <div className="text-base font-semibold">WILQ</div>
              <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
                {[...primarySurfaceRoutes, ...secondarySurfaceRoutes].map((route) => (
                  <Link
                    key={route.path}
                    to={route.path}
                    className="whitespace-nowrap rounded-md border border-line px-3 py-2 text-xs [&.active]:border-ink [&.active]:bg-ink [&.active]:text-white"
                  >
                    {route.label}
                  </Link>
                ))}
              </div>
            </>
          )}
        </header>
        <Outlet />
      </div>
    </div>
  );
}

function SurfaceNavSection({
  label,
  routes,
  linkClassName = "text-sm text-slate-700 hover:bg-slate-100 [&.active]:bg-ink [&.active]:text-white"
}: {
  label?: string;
  routes: readonly SurfaceRoute[];
  linkClassName?: string;
}) {
  return (
    <div className="space-y-1">
      {label ? (
        <div className="px-3 pt-1 text-[11px] font-semibold uppercase tracking-normal text-slate-400">
          {label}
        </div>
      ) : null}
      {routes.map((route) => {
        const Icon = route.icon;
        if (!Icon) return null;
        return (
          <Link
            key={route.path}
            to={route.path}
            title={route.firstScreenIntent}
            className={`flex h-10 items-center gap-3 rounded-md px-3 ${linkClassName}`}
          >
            <Icon aria-hidden="true" size={17} />
            <span>{route.label}</span>
          </Link>
        );
      })}
    </div>
  );
}

import { Link, Outlet } from "@tanstack/react-router";
import { primarySurfaceRoutes } from "../routes/surfaceRegistry";

export function Shell() {
  return (
    <div className="min-h-screen bg-surface">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-line bg-white lg:block">
        <div className="border-b border-line px-5 py-4">
          <div className="text-lg font-semibold tracking-normal">WILQ</div>
          <div className="text-xs uppercase tracking-normal text-slate-500">
            System marketingowy Ekologus
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {primarySurfaceRoutes.map((route) => {
            const Icon = route.icon;
            if (!Icon) return null;
            return (
              <Link
                key={route.path}
                to={route.path}
                className="flex h-10 items-center gap-3 rounded-md px-3 text-sm text-slate-700 hover:bg-slate-100 [&.active]:bg-ink [&.active]:text-white"
              >
                <Icon aria-hidden="true" size={17} />
                <span>{route.label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-line bg-white/95 px-4 py-3 backdrop-blur lg:hidden">
          <div className="text-base font-semibold">WILQ</div>
          <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
            {primarySurfaceRoutes.map((route) => (
              <Link
                key={route.path}
                to={route.path}
                className="whitespace-nowrap rounded-md border border-line px-3 py-2 text-xs [&.active]:border-ink [&.active]:bg-ink [&.active]:text-white"
              >
                {route.label}
              </Link>
            ))}
          </div>
        </header>
        <Outlet />
      </div>
    </div>
  );
}

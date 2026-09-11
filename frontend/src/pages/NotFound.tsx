import { PageShell } from "../components/common/PageShell";

export function NotFound() {
  return (
    <PageShell className="mx-auto w-full max-w-xl px-4 py-24 text-center">
      <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-teal-700">404</p>
      <h1 className="mt-3 text-3xl font-extrabold text-slate-900">Page not found</h1>
      <p className="mt-3 text-sm text-slate-600">That route does not exist. Return home or open a conversation.</p>
      <a className="mt-6 inline-block font-bold text-teal-800" href="/">
        Back to home
      </a>
    </PageShell>
  );
}

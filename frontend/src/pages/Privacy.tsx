import { PageShell } from "../components/common/PageShell";

export function Privacy() {
  return (
    <PageShell className="mx-auto w-full max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-extrabold text-slate-900">Privacy</h1>
      <div className="mt-6 space-y-5 text-sm leading-7 text-slate-600">
        <p>MediAssist stores account details and conversation history so you can return to previous chats. Chat content is not shared between accounts.</p>
        <ul className="list-disc space-y-2 pl-5">
          <li>Passwords are stored as hashes, not as plain text.</li>
          <li>Sign-in uses HTTP-only cookies rather than tokens in page scripts.</li>
          <li>You can rename or delete conversations from the sidebar.</li>
        </ul>
        <p>This educational project is not a HIPAA-certified clinical service. Do not assume records are encrypted at rest, anonymised, or automatically deleted unless a hospital-grade deployment is added later.</p>
      </div>
    </PageShell>
  );
}

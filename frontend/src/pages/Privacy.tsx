import { PageShell } from "../components/common/PageShell";

export function Privacy() {
  return (
    <PageShell className="mx-auto w-full max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-extrabold text-slate-900">Privacy</h1>
      <p className="mt-4 text-sm leading-7 text-slate-600">
        MediAssist stores account details and conversation history in MongoDB so you can return to previous chats. Passwords are hashed. Authentication uses HTTP-only cookies. Chat content is not shared between accounts. This educational project is not a HIPAA-certified clinical service.
      </p>
    </PageShell>
  );
}

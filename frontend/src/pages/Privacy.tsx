import { AlertTriangle, Ban, BookOpen, ShieldAlert } from "lucide-react";
import { PageShell } from "../components/common/PageShell";
import { TriageBadge } from "../components/medical/TriageBadge";

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

export function Safety() {
  return (
    <PageShell className="mx-auto w-full max-w-4xl px-4 py-12">
      <h1 className="text-3xl font-extrabold text-slate-900">Safety</h1>
      <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-600">
        MediAssist provides general medical information and urgency guidance. It does not diagnose, prescribe, or replace emergency services. Always seek in-person care when you are unsure or symptoms are severe.
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <article className="rounded-3xl border border-teal-100 bg-white p-6 shadow-sm">
          <AlertTriangle className="text-red-600" size={22} />
          <h2 className="mt-3 text-lg font-extrabold text-slate-900">Emergency symptoms are flagged</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Descriptions that suggest a medical emergency, such as crushing chest pain or sudden weakness, receive a visible emergency banner. If that happens, seek urgent in-person care or call your local emergency number.
          </p>
        </article>
        <article className="rounded-3xl border border-teal-100 bg-white p-6 shadow-sm">
          <Ban className="text-teal-700" size={22} />
          <h2 className="mt-3 text-lg font-extrabold text-slate-900">No prescriptions or doses</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Requests for a specific drug, dose, or prescription are refused. Dosing depends on your history and needs a qualified clinician or pharmacist.
          </p>
        </article>
        <article className="rounded-3xl border border-teal-100 bg-white p-6 shadow-sm">
          <ShieldAlert className="text-teal-700" size={22} />
          <h2 className="mt-3 text-lg font-extrabold text-slate-900">Triage is guidance, not a diagnosis</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Every answer is labelled by urgency so you can see how serious the retrieved information appears. The label is not a clinical assessment.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <TriageBadge level="self_care" />
            <TriageBadge level="consult_doctor" />
            <TriageBadge level="emergency" />
          </div>
        </article>
        <article className="rounded-3xl border border-teal-100 bg-white p-6 shadow-sm">
          <BookOpen className="text-teal-700" size={22} />
          <h2 className="mt-3 text-lg font-extrabold text-slate-900">Answers stay tied to sources</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Responses are generated from retrieved medical notes, with citations shown when sources are found. The assistant cannot examine you, order tests, or replace a qualified professional.
          </p>
        </article>
      </div>
    </PageShell>
  );
}

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

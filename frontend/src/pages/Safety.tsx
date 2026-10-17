import { AlertTriangle, Ban, BookOpen, ShieldAlert } from "lucide-react";
import { PageShell } from "../components/common/PageShell";
import { TriageBadge } from "../components/medical/TriageBadge";

export function Safety() {
  return (
    <PageShell className="mx-auto w-full max-w-4xl px-4 py-12">
      <h1 className="text-3xl font-extrabold text-slate-900">Safety</h1>
      <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-600">
        MediAssist provides general medical information and urgency guidance. It does not diagnose, prescribe, or replace emergency services. If you think you are having an emergency, call 108 or local emergency services now.
      </p>
      <a href="tel:108" className="mt-4 inline-flex min-h-11 items-center rounded-full bg-red-600 px-4 text-sm font-extrabold text-white hover:bg-red-700">
        Call 108
      </a>

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

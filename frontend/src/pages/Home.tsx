import { Link, useLocation } from "react-router-dom";
import { ShieldCheck, BookOpen, Activity, Lock, MapPin } from "lucide-react";
import { useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/common/Button";
import { scrollToSection } from "../utils/scroll";
import { PageShell } from "../components/common/PageShell";

const features = [
  { icon: BookOpen, title: "General and medical chat", body: "Ask everyday, coding, or travel questions in the same chat. Symptom questions still match curated medical notes before a response is generated." },
  { icon: MapPin, title: "Body map for location", body: "Tap a body region when it is hard to describe symptoms in words. The map helps locate discomfort; it does not diagnose." },
  { icon: ShieldCheck, title: "Safety-first triage", body: "Emergency wording is flagged and prescription or dosage requests are refused." },
  { icon: Activity, title: "Transparent sources", body: "Each answer can show supporting documents so you can see where the information came from." },
  { icon: Lock, title: "Private conversations", body: "Chats are stored per account. Other users cannot open your history." },
];

const steps = [
  "Describe symptoms in everyday language, or mark a body region.",
  "Retrieve matching passages from the knowledge base.",
  "Apply safety rules and triage.",
  "Generate a grounded response.",
  "Show supporting sources and urgency guidance.",
];

export function Home() {
  const { user } = useAuth();
  const location = useLocation();

  useEffect(() => {
    if (location.hash !== "#how-it-works") return;
    const timer = window.setTimeout(() => scrollToSection("how-it-works"), 50);
    return () => window.clearTimeout(timer);
  }, [location.hash, location.key]);
  return (
    <PageShell>
        <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-16 lg:grid-cols-2">
          <div>
            <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-teal-700">Medical information assistant</p>
            <h1 className="mt-3 text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
              Understand your symptoms with grounded medical AI
            </h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-slate-600">
              Describe symptoms in your own words, or tap a body map to mark where it hurts. MediAssist retrieves matching notes from a curated medical collection, then shows possible explanations, urgency guidance, and sources. It is not a diagnosis and does not replace a clinician.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to={user ? "/chat" : "/register"}>
                <Button size="lg">Start a conversation</Button>
              </Link>
              <Button
                type="button"
                variant="secondary"
                size="lg"
                onClick={() => {
                  scrollToSection("how-it-works");
                  window.history.replaceState(null, "", "/#how-it-works");
                }}
              >
                How it works
              </Button>
              {user ? (
                <Link to="/dashboard" className="inline-flex min-h-12 items-center px-2 text-sm font-bold text-teal-800 hover:underline">
                  Open your dashboard
                </Link>
              ) : null}
            </div>
          </div>
          <img src="/images/hero-rag.png" alt="Symptom description matched to medical documents" width={960} height={640} decoding="async" fetchPriority="high" className="h-auto w-full rounded-[2rem] object-cover shadow-xl shadow-teal-900/10" />
        </section>

        <section className="mx-auto grid max-w-6xl gap-4 px-4 pb-16 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {features.map((item) => (
            <article key={item.title} className="rounded-3xl border border-teal-100 bg-white p-5 shadow-sm">
              <item.icon className="text-teal-700" size={22} />
              <h2 className="mt-3 text-base font-extrabold text-slate-900">{item.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.body}</p>
            </article>
          ))}
        </section>

        <section id="how-it-works" className="scroll-mt-24 bg-white py-16">
          <div className="mx-auto max-w-6xl px-4">
            <h2 className="text-3xl font-extrabold text-slate-900">How it works</h2>
            <ol className="mt-8 grid gap-4 md:grid-cols-5">
              {steps.map((step, index) => (
                <li key={step} className="rounded-3xl bg-[#f4f8f7] p-4">
                  <span className="text-xs font-extrabold text-teal-700">0{index + 1}</span>
                  <p className="mt-2 text-sm font-bold leading-6 text-slate-800">{step}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16">
          <div className="rounded-[2rem] border border-teal-100 bg-teal-900 px-6 py-10 text-white md:px-10">
            <h2 className="text-3xl font-extrabold">Designed for information, not diagnosis.</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-teal-50">
              Emergency symptoms are highlighted. Prescription and dosage questions are refused. Answers stay tied to retrieved documents, with a visible medical disclaimer.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link to="/safety">
                <Button variant="secondary">Read safety notes</Button>
              </Link>
              <Link to={user ? "/chat" : "/login"}>
                <Button>Start a conversation</Button>
              </Link>
            </div>
          </div>
        </section>
    </PageShell>
  );
}

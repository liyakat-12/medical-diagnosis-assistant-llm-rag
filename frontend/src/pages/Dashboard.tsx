import { useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BarChart3, History, MessageSquarePlus, PersonStanding, ShieldCheck } from "lucide-react";
import { PageShell } from "../components/common/PageShell";
import { EmptyState, ErrorState, SectionHeading, Skeleton } from "../components/insights/States";
import { useAuth } from "../context/AuthContext";
import { useAsync } from "../hooks/useAsync";
import { cn } from "../lib/cn";
import { listChats, listMessages } from "../services/chat";
import { getEvaluationOverview } from "../services/evaluation";
import type { Chat } from "../types";
import type { EvaluationOverview } from "../types/evaluation";
import { buildDashboardStats, glanceMetrics, latestRun, type AsyncState, type GlanceMetric, type LatestReply, type StatCard } from "../utils/dashboardStats";
import { formatCategory, formatPercent, formatScore } from "../utils/evaluationMetrics";
import { formatDate } from "../utils/dates";

async function loadLatestReply(): Promise<LatestReply> {
  const chats = await listChats();
  const latest = chats.find((chat) => chat.message_count > 0);
  if (!latest) return null;
  const messages = await listMessages(latest.id);
  const reply = [...messages].reverse().find((message) => message.role === "assistant");
  return reply ? { chatId: latest.id, chatTitle: latest.title, citations: reply.citations.length } : null;
}

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export const quickActions = [
  { to: "/chat?map=1", icon: PersonStanding, title: "Symptom body map", body: "Mark where it hurts, then describe it." },
  { to: "/history", icon: History, title: "Previous conversations", body: "Search and reopen saved chats." },
  { to: "/evaluation", icon: BarChart3, title: "Evaluation dashboard", body: "Retrieval metrics and charts." },
];

const focusRing = "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 motion-reduce:transition-none";

function StatValue({ stat }: { stat: StatCard }) {
  const { display } = stat;
  if (display.kind === "loading") {
    return (
      <>
        <Skeleton className="mt-2 h-8 w-20" />
        <Skeleton className="mt-2 h-3 w-28" />
      </>
    );
  }
  if (display.kind === "error") return <p className="mt-2 text-sm font-bold text-rose-700">Could not load</p>;
  if (display.kind === "unavailable") {
    return (
      <>
        <p className="mt-2 text-sm font-bold text-slate-500">Not available</p>
        <p className="mt-1 line-clamp-3 text-xs leading-5 text-slate-500">{display.reason}</p>
      </>
    );
  }
  return (
    <>
      <p className="mt-1.5 text-2xl font-extrabold tabular-nums tracking-tight text-[#0b1f33] sm:text-3xl">{display.value}</p>
      {display.detail ? <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{display.detail}</p> : <span className="mt-1 block min-h-5" />}
    </>
  );
}

function StatTile({ stat }: { stat: StatCard }) {
  const accent = stat.id === "mrr" ? "bg-[#0b1f33]" : stat.id === "recall1" || stat.id === "conversations" ? "bg-teal-700" : "bg-slate-300";
  const body = (
    <>
      <dt className="text-xs font-bold text-slate-500" title={stat.hint}>
        {stat.label}
      </dt>
      <dd className="flex flex-1 flex-col">
        <StatValue stat={stat} />
      </dd>
      <span aria-hidden className={cn("mt-3 h-1 w-8 rounded-full", accent)} />
      {stat.href && stat.linkLabel ? <span className="sr-only">{stat.linkLabel}</span> : null}
    </>
  );
  const className = "flex h-full min-w-0 flex-col rounded-2xl border border-slate-200 bg-white px-4 py-4";
  if (!stat.href) return <div className={className}>{body}</div>;
  return (
    <Link to={stat.href} title={stat.hint} className={cn(className, "transition-colors hover:border-teal-700", focusRing)}>
      {body}
    </Link>
  );
}

export function Dashboard() {
  const { user } = useAuth();
  const overview = useAsync(getEvaluationOverview);
  const chats = useAsync(useCallback(() => listChats(), []));
  const latest = useAsync(loadLatestReply);

  const stats = useMemo(() => buildDashboardStats(overview.state, chats.state, latest.state), [overview.state, chats.state, latest.state]);
  const failed = [overview, chats, latest].filter((item) => item.state.status === "error");
  const firstName = user?.name?.split(" ")[0] || "there";

  return (
    <PageShell>
      <section className="bg-[linear-gradient(165deg,#0b1f33_0%,#102a44_100%)] text-white">
        <div className="mx-auto grid max-w-7xl items-center gap-8 px-4 py-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(18rem,0.85fr)] lg:py-14">
          <div className="max-w-xl">
            <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-teal-300">MediAssist workspace</p>
            <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-white sm:text-4xl [text-wrap:balance]">
              {greeting()}, {firstName}.
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-200 sm:text-base sm:leading-7">
              Ask about symptoms in your own words. MediAssist finds matching reference notes, cites them, and flags urgent warning signs. It does not diagnose.
            </p>
            <Link
              to="/chat"
              className="mt-6 inline-flex min-h-12 items-center gap-2 rounded-full bg-teal-500 px-6 text-sm font-extrabold text-[#0b1f33] transition-colors hover:bg-teal-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-200 motion-reduce:transition-none"
            >
              <MessageSquarePlus size={18} aria-hidden /> Start a conversation
            </Link>
          </div>
          <nav aria-label="Quick actions" className="grid gap-3">
            {quickActions.map((action) => (
              <Link
                key={action.to}
                to={action.to}
                className="group flex items-center gap-3 rounded-2xl border border-white/10 bg-[#10283f] px-4 py-3.5 transition-colors hover:border-teal-300/60 hover:bg-[#14324c] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-300 motion-reduce:transition-none"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-400/15 text-teal-200">
                  <action.icon size={18} aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-bold text-white">{action.title}</span>
                  <span className="block text-xs leading-5 text-slate-300">{action.body}</span>
                </span>
                <ArrowRight size={16} className="shrink-0 text-slate-400 transition-transform group-hover:translate-x-0.5 group-hover:text-teal-200 motion-reduce:transition-none motion-reduce:group-hover:translate-x-0" aria-hidden />
              </Link>
            ))}
          </nav>
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-4 py-8">
        {failed.length ? (
          <div className="mb-4">
            <ErrorState
              title="Some dashboard data could not be loaded"
              message={failed[0].state.status === "error" ? failed[0].state.message : ""}
              onRetry={() => failed.forEach((item) => item.reload())}
            />
          </div>
        ) : null}

        <section aria-labelledby="stats-title">
          <h2 id="stats-title" className="sr-only">Key figures</h2>
          <dl className="grid grid-cols-2 items-stretch gap-3 md:grid-cols-3 xl:grid-cols-6" aria-busy={stats.some((stat) => stat.display.kind === "loading")}>
            {stats.map((stat) => (
              <div key={stat.id} className="min-w-0">
                <StatTile stat={stat} />
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs leading-5 text-slate-500">Retrieval metrics show whether the expected reference note was found. They are not diagnostic accuracy.</p>
        </section>

        <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
          <section aria-labelledby="recent-title" className="min-w-0">
            <SectionHeading
              id="recent-title"
              eyebrow="Activity"
              title="Recent conversations"
              actions={
                <Link to="/history" className={cn("inline-flex min-h-9 items-center rounded-full px-3 text-sm font-bold text-teal-800 hover:bg-teal-50", focusRing)}>
                  View all
                </Link>
              }
            />
            <div className="mt-4">
              <RecentChats state={chats.state} />
            </div>
          </section>

          <section aria-labelledby="glance-title" className="min-w-0">
            <SectionHeading
              id="glance-title"
              eyebrow="Evaluation"
              title="Retrieval at a glance"
              actions={
                <Link to="/evaluation" className={cn("inline-flex min-h-9 items-center rounded-full px-3 text-sm font-bold text-teal-800 hover:bg-teal-50", focusRing)}>
                  Open dashboard
                </Link>
              }
            />
            <div className="mt-4">
              <RetrievalGlance state={overview.state} />
            </div>
          </section>
        </div>
      </div>
    </PageShell>
  );
}

export function RecentChats({ state }: { state: AsyncState<Chat[]> }) {
  if (state.status === "loading") {
    return (
      <ul className="divide-y divide-slate-200 rounded-2xl border border-slate-200 bg-white" aria-busy>
        {[0, 1, 2].map((index) => (
          <li key={index} className="px-4 py-4">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="mt-2 h-3 w-1/3" />
          </li>
        ))}
      </ul>
    );
  }
  if (state.status === "error") return <p className="text-sm text-slate-500">Conversations are unavailable right now.</p>;
  if (!state.data.length) {
    return (
      <EmptyState
        title="No conversations yet"
        action={
          <Link to="/chat" className={cn("text-sm font-bold text-teal-800 hover:underline", focusRing)}>
            Start your first conversation
          </Link>
        }
      >
        Your saved chats will appear here. Only you can see them.
      </EmptyState>
    );
  }
  return (
    <ul className="divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-white">
      {state.data.slice(0, 6).map((chat) => (
        <li key={chat.id}>
          <Link
            to={`/chat/${chat.id}`}
            className={cn("flex items-center gap-3 px-4 py-3.5 transition-colors hover:bg-slate-50", focusRing)}
          >
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-bold text-[#0b1f33]">{chat.title}</span>
              <span className="mt-0.5 block text-xs text-slate-500">{formatDate(chat.last_message_at || chat.updated_at || chat.created_at)}</span>
            </span>
            <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-bold tabular-nums text-slate-600">
              {chat.message_count} <span className="font-semibold text-slate-500">{chat.message_count === 1 ? "message" : "messages"}</span>
            </span>
            <ArrowRight size={15} className="shrink-0 text-slate-400" aria-hidden />
          </Link>
        </li>
      ))}
    </ul>
  );
}

function GlanceRow({ item }: { item: GlanceMetric }) {
  const shown = item.kind === "recall" ? formatPercent(item.value) : formatScore(item.value);
  const width = item.value === null || Number.isNaN(item.value) ? 0 : Math.max(0, Math.min(item.value, 1)) * 100;
  return (
    <li className="grid grid-cols-[5.5rem_minmax(0,1fr)_3.5rem] items-center gap-3 text-xs">
      <span className="font-bold text-slate-700">
        {item.label}
        {item.kind === "rank" ? <span className="mt-0.5 block text-[11px] font-medium text-slate-500">Rank score</span> : null}
      </span>
      <span className="h-2 overflow-hidden rounded-full bg-slate-100" title={`${item.label}: ${shown}`}>
        {width > 0 ? <span className={cn("block h-full rounded-full", item.kind === "rank" ? "bg-[#0b1f33]" : "bg-teal-700")} style={{ width: `${width}%` }} /> : null}
      </span>
      <span className="text-right font-bold tabular-nums text-[#0b1f33]">
        {shown}
        {item.value === null ? <span className="sr-only"> unavailable</span> : null}
      </span>
    </li>
  );
}

export function RetrievalGlance({ state }: { state: AsyncState<EvaluationOverview> }) {
  if (state.status === "loading") {
    return (
      <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5" aria-busy>
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-2.5 w-full" />
        <Skeleton className="h-2.5 w-5/6" />
        <Skeleton className="h-2.5 w-4/6" />
      </div>
    );
  }
  if (state.status === "error") return <p className="text-sm text-slate-500">Evaluation results are unavailable right now.</p>;
  const run = latestRun(state.data);
  if (!run) {
    return (
      <EmptyState title="No stored evaluation run">
        Run <code className="rounded bg-slate-100 px-1">python evaluation/evaluate_kb_phase2.py</code> to generate retrieval metrics.
      </EmptyState>
    );
  }
  const safety = Object.entries(run.safety).filter(([, check]) => check.n > 0);
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <p className="text-xs leading-5 text-slate-500">
        Run <span className="font-bold text-slate-700">{run.label}</span>
        {" · "}
        {run.metrics.n} labelled queries
        {" · "}
        {formatDate(run.generated_at)}
      </p>
      <ul className="mt-4 space-y-3">
        {glanceMetrics(run).map((item) => (
          <GlanceRow key={item.id} item={item} />
        ))}
      </ul>
      <p className="mt-3 text-xs leading-5 text-slate-500">Recall uses a 0–100% scale. MRR is a ranking score from 0 to 1, not a recall percentage.</p>
      {safety.length ? <SafetyChecks safety={safety} /> : null}
    </div>
  );
}

function SafetyChecks({ safety }: { safety: [string, EvaluationOverview["retrieval_runs"][number]["safety"][string]][] }) {
  return (
    <div className="mt-5 border-t border-slate-200 pt-4">
      <p className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
        <ShieldCheck size={14} className="text-teal-700" aria-hidden /> Safety checks in this run
      </p>
      <ul className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        {safety.map(([name, check]) => (
          <li key={name} className="flex justify-between gap-2">
            <span className="text-slate-600">{formatCategory(name)}</span>
            <span className={cn("font-bold tabular-nums", check.passed === check.n ? "text-teal-800" : "text-rose-700")}>
              {check.passed}/{check.n}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

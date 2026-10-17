import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { PageShell } from "../components/common/PageShell";
import { Button } from "../components/common/Button";
import { Input } from "../components/common/Input";
import { useAuth } from "../context/AuthContext";
import { isValidEmail } from "../utils/validation";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from || "/chat";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const next: Record<string, string> = {};
    if (!isValidEmail(email)) next.email = "Enter a valid email.";
    if (!password) next.password = "Password is required.";
    setErrors(next);
    if (Object.keys(next).length) return;
    setBusy(true);
    setServerError("");
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (error) {
      setServerError(error instanceof Error ? error.message : "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell className="mx-auto grid w-full max-w-md px-4 py-16">
        <div className="rounded-[2rem] border border-teal-100 bg-white p-8 shadow-sm">
          <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-teal-700">MediAssist</p>
          <h1 className="mt-2 text-3xl font-extrabold text-slate-900">Welcome back</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">How to log in: enter your email and password, then click Sign in.</p>
          <div className="mt-5 rounded-2xl border border-teal-200 bg-teal-50 p-4">
            <p className="text-xs font-extrabold uppercase tracking-wide text-teal-800">Demo login (easy to try)</p>
            <ol className="mt-2 list-decimal space-y-1 pl-4 text-sm leading-6 text-slate-700">
              <li>Click Fill demo details, or type the email and password below.</li>
              <li>Click Sign in.</li>
              <li>You will open the chat screen.</li>
            </ol>
            <p className="mt-3 text-sm font-semibold text-slate-800">Email: demo@clinic.local</p>
            <p className="text-sm font-semibold text-slate-800">Password: demo123</p>
            <Button
              type="button"
              variant="secondary"
              className="mt-3 w-full"
              onClick={() => {
                setEmail("demo@clinic.local");
                setPassword("demo123");
                setErrors({});
                setServerError("");
              }}
            >
              Fill demo details
            </Button>
          </div>
          <form className="mt-6 space-y-4" onSubmit={(event) => void onSubmit(event)}>
            <Input label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} error={errors.email} autoComplete="email" />
            <Input label="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} error={errors.password} autoComplete="current-password" />
            {serverError ? (
              <p className="text-sm font-semibold text-rose-600" role="alert">
                {serverError}
              </p>
            ) : null}
            <Button className="w-full" type="submit" disabled={busy}>
              {busy ? "Signing in..." : "Sign in"}
            </Button>
          </form>
          <p className="mt-4 text-sm text-slate-600">
            No account yet?{" "}
            <Link className="font-bold text-teal-800" to="/register">
              Create one
            </Link>
          </p>
        </div>
    </PageShell>
  );
}

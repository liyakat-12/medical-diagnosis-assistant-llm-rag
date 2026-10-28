import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PageShell } from "../components/common/PageShell";
import { Button } from "../components/common/Button";
import { Input } from "../components/common/Input";
import { useAuth } from "../context/AuthContext";
import { isValidEmail, passwordIssues } from "../utils/validation";

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState("");
  const [busy, setBusy] = useState(false);
  const strength = useMemo(() => passwordIssues(password), [password]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const next: Record<string, string> = {};
    if (name.trim().length < 2) next.name = "Name is required.";
    if (!isValidEmail(email)) next.email = "Enter a valid email.";
    if (strength.length) next.password = strength[0];
    if (password !== confirm) next.confirm = "Passwords do not match.";
    setErrors(next);
    if (Object.keys(next).length) return;
    setBusy(true);
    setServerError("");
    try {
      await register(name.trim(), email, password);
      navigate("/chat", { replace: true });
    } catch (error) {
      setServerError(error instanceof Error ? error.message : "Unable to create your account.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell className="mx-auto grid w-full max-w-md px-4 py-16">
        <div className="min-w-0 rounded-[2rem] border border-teal-100 bg-white p-5 shadow-sm sm:p-8">
          <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-teal-700">MediAssist</p>
          <h1 className="mt-2 text-3xl font-extrabold text-slate-900">Create your account</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">Your conversations stay private to this account.</p>
          <form className="mt-6 space-y-4" onSubmit={(event) => void onSubmit(event)}>
            <Input label="Name" value={name} onChange={(event) => setName(event.target.value)} error={errors.name} autoComplete="name" />
            <Input label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} error={errors.email} autoComplete="email" />
            <Input label="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} error={errors.password} autoComplete="new-password" />
            <Input label="Confirm password" type="password" value={confirm} onChange={(event) => setConfirm(event.target.value)} error={errors.confirm} autoComplete="new-password" />
            {serverError ? (
              <p className="text-sm font-semibold text-rose-600" role="alert">
                {serverError}
              </p>
            ) : null}
            <Button className="w-full" type="submit" disabled={busy}>
              {busy ? "Creating account..." : "Get started"}
            </Button>
          </form>
          <p className="mt-4 text-sm text-slate-600">
            Already registered?{" "}
            <Link className="font-bold text-teal-800" to="/login">
              Sign in
            </Link>
          </p>
          <p className="mt-3 text-xs leading-5 text-slate-500">
            Want to try first? Use the demo login on the sign-in page: demo@clinic.local / demo123
          </p>
        </div>
    </PageShell>
  );
}

import { useState, type FormEvent } from "react";
import { PageShell } from "../components/common/PageShell";
import { Button } from "../components/common/Button";
import { Input } from "../components/common/Input";
import { Avatar } from "../components/common/Spinner";
import { useAuth } from "../context/AuthContext";
import { updateProfile } from "../services/auth";
import { formatDate } from "../utils/dates";

export function Profile() {
  const { user, logout, setUser } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      setUser(await updateProfile({ name: name.trim() }));
      setMessage("Profile updated.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to update profile.");
    } finally {
      setBusy(false);
    }
  }

  if (!user) return null;

  return (
    <PageShell className="mx-auto w-full max-w-xl px-4 py-12">
        <div className="rounded-[2rem] border border-teal-100 bg-white p-8 shadow-sm">
          <div className="flex items-center gap-3">
            <Avatar name={user.name} />
            <div>
              <h1 className="text-2xl font-extrabold text-slate-900">{user.name}</h1>
              <p className="text-sm text-slate-600">{user.email}</p>
            </div>
          </div>
          <dl className="mt-6 space-y-2 text-sm text-slate-600">
            <div className="flex justify-between">
              <dt>Member since</dt>
              <dd className="font-bold text-slate-900">{formatDate(user.created_at)}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Last login</dt>
              <dd className="font-bold text-slate-900">{formatDate(user.last_login)}</dd>
            </div>
          </dl>
          <form className="mt-6 space-y-4" onSubmit={(event) => void onSubmit(event)}>
            <Input label="Display name" value={name} onChange={(event) => setName(event.target.value)} />
            {message ? <p className="text-sm font-semibold text-teal-800">{message}</p> : null}
            <Button type="submit" disabled={busy}>
              {busy ? "Saving..." : "Save changes"}
            </Button>
          </form>
          <Button variant="secondary" className="mt-6" onClick={() => void logout()}>
            Logout
          </Button>
        </div>
    </PageShell>
  );
}

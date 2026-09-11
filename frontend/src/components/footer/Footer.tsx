import { Link } from "react-router-dom";
import { Stethoscope } from "lucide-react";

export function Footer() {
  return (
    <footer className="mt-auto border-t border-teal-100 bg-white">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:grid-cols-3">
        <div>
          <p className="flex items-center gap-2 font-extrabold text-teal-900">
            <Stethoscope size={18} /> MediAssist
          </p>
          <p className="mt-3 max-w-sm text-sm leading-6 text-slate-600">
            Evidence-grounded symptom information and triage guidance. Not a substitute for a qualified clinician.
          </p>
        </div>
        <div className="space-y-2 text-sm font-bold text-slate-700">
          <Link className="block hover:text-teal-800" to="/">
            Home
          </Link>
          <Link className="block hover:text-teal-800" to="/safety">
            Safety
          </Link>
          <Link className="block hover:text-teal-800" to="/privacy">
            Privacy
          </Link>
        </div>
        <p className="text-sm text-slate-500">© {new Date().getFullYear()} MediAssist. Educational research project.</p>
      </div>
    </footer>
  );
}

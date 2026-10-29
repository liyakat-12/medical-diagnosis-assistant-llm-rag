import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { Menu, Stethoscope, X } from "lucide-react";
import { useState, type MouseEvent } from "react";
import { useAuth } from "../../context/AuthContext";
import { Button } from "../common/Button";
import { cn } from "../../lib/cn";
import { scrollToSection } from "../../utils/scroll";

const publicLinks = [
  { to: "/", label: "Home" },
  { to: "/#how-it-works", label: "How it works", hash: "how-it-works" },
  { to: "/safety", label: "Safety" },
];

const memberLinks = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/chat", label: "Chat" },
  { to: "/history", label: "History" },
  { to: "/evaluation", label: "Evaluation" },
  { to: "/profile", label: "Profile" },
];

export function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const hideOnChat = location.pathname.startsWith("/chat") || location.pathname === "/history";
  const desktopPublic = user ? publicLinks.filter((link) => link.to !== "/") : publicLinks;

  function goToHowItWorks(event: MouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    setOpen(false);
    if (location.pathname === "/") {
      scrollToSection("how-it-works");
      if (location.hash !== "#how-it-works") {
        window.history.replaceState(null, "", "/#how-it-works");
      }
      return;
    }
    navigate({ pathname: "/", hash: "how-it-works" });
  }

  return (
    <header className={cn("sticky top-0 z-40 border-b border-teal-100 bg-white/90 backdrop-blur", hideOnChat && "lg:hidden")}>
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 overflow-hidden px-4">
        <NavLink to={user ? "/dashboard" : "/"} className="flex shrink-0 items-center gap-2 font-extrabold text-teal-900">
          <span className="grid h-9 w-9 place-items-center rounded-2xl bg-teal-700 text-white">
            <Stethoscope size={18} />
          </span>
          MediAssist
        </NavLink>
        <nav className={cn("hidden items-center gap-5 text-sm font-bold text-slate-600", user ? "lg:flex" : "md:flex")}>
          {desktopPublic.map((link) =>
            link.hash ? (
              <a key={link.to} href="/#how-it-works" className="hover:text-teal-800" onClick={goToHowItWorks}>
                {link.label}
              </a>
            ) : (
              <NavLink key={link.to} to={link.to} end className={({ isActive }) => cn("hover:text-teal-800", isActive && "text-teal-800")}>
                {link.label}
              </NavLink>
            ),
          )}
          {user ? (
            <>
              <span aria-hidden className="h-5 w-px bg-slate-200" />
              {memberLinks.map((link) => (
                <NavLink key={link.to} to={link.to} className={({ isActive }) => cn("hover:text-teal-800", isActive && "text-teal-800")}>
                  {link.label}
                </NavLink>
              ))}
              <Button variant="secondary" size="sm" onClick={() => void logout()}>
                Logout
              </Button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={({ isActive }) => cn("hover:text-teal-800", isActive && "text-teal-800")}>
                Login
              </NavLink>
              <NavLink to="/register" className="rounded-full bg-teal-700 px-5 py-2.5 text-sm font-bold text-white hover:bg-teal-800">
                Get started
              </NavLink>
            </>
          )}
        </nav>
        <button className={cn("grid h-11 w-11 place-items-center rounded-xl", user ? "lg:hidden" : "md:hidden")} onClick={() => setOpen((value) => !value)} aria-label="Toggle navigation" aria-expanded={open}>
          {open ? <X /> : <Menu />}
        </button>
      </div>
      {open ? (
        <nav className={cn("space-y-2 border-t border-teal-100 bg-white px-4 py-4", user ? "lg:hidden" : "md:hidden")}>
          {[...publicLinks, ...(user ? memberLinks : [{ to: "/login", label: "Login" }, { to: "/register", label: "Get started" }])].map((link) =>
            "hash" in link && link.hash ? (
              <a
                key={link.to}
                href="/#how-it-works"
                className="block rounded-xl px-3 py-2 font-bold text-slate-700 hover:bg-teal-50"
                onClick={goToHowItWorks}
              >
                {link.label}
              </a>
            ) : (
              <NavLink key={link.to} to={link.to} className="block rounded-xl px-3 py-2 font-bold text-slate-700 hover:bg-teal-50" onClick={() => setOpen(false)}>
                {link.label}
              </NavLink>
            ),
          )}
          {user ? (
            <Button variant="secondary" className="w-full" onClick={() => void logout()}>
              Logout
            </Button>
          ) : null}
        </nav>
      ) : null}
    </header>
  );
}

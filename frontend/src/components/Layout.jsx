import { useAuth } from "@/context/AuthContext";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Notifications } from "@/components/Notifications";
import { LayoutDashboard, Users, LogOut, FileCheck2, ShieldCheck, GanttChartSquare } from "lucide-react";

export function Layout({ children, activeClientName }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const loc = useLocation();
  const isPro = user?.account_type === "PRO";

  const nav = [
    { to: "/dashboard", label: "Tableau de bord", icon: LayoutDashboard, testId: "nav-dashboard" },
  ];
  if (isPro) nav.push({ to: "/clients", label: "Clients", icon: Users, testId: "nav-clients" });
  if (isPro) nav.push({ to: "/portefeuille", label: "Portefeuille", icon: GanttChartSquare, testId: "nav-portefeuille" });

  return (
    <div className="min-h-screen paper-bg flex flex-col">
      <header className="sticky top-0 z-30 bg-[#0F2B48] text-white border-b border-black/20">
        <div className="max-w-[1400px] mx-auto px-5 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link to="/dashboard" className="flex items-center gap-2" data-testid="brand-link">
              <ShieldCheck className="text-blue-300" size={22} />
              <span className="font-display font-extrabold text-lg tracking-tight">CONFORMISTE</span>
              <span className={`ml-1 text-[10px] font-semibold px-2 py-0.5 rounded-full ${isPro ? "bg-blue-500" : "bg-emerald-500"}`}>
                {user?.account_type}
              </span>
            </Link>
            <nav className="hidden md:flex items-center gap-1">
              {nav.map((n) => {
                const active = loc.pathname.startsWith(n.to);
                return (
                  <Link key={n.to} to={n.to} data-testid={n.testId}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                      active ? "bg-white/15 text-white" : "text-blue-100 hover:bg-white/10"
                    }`}>
                    <n.icon size={16} /> {n.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            {isPro && activeClientName && (
              <span className="hidden sm:flex items-center gap-2 text-xs bg-white/10 px-3 py-1.5 rounded-lg" data-testid="active-client-badge">
                <FileCheck2 size={14} className="text-blue-300" /> Client actif : <b>{activeClientName}</b>
              </span>
            )}
            <span className="hidden sm:block text-sm text-blue-100">{user?.name}</span>
            <Notifications />
            <Button variant="ghost" size="sm" data-testid="logout-button"
              onClick={async () => { await logout(); navigate("/"); }}
              className="text-blue-100 hover:text-white hover:bg-white/10">
              <LogOut size={16} className="mr-1" /> Quitter
            </Button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-[1400px] w-full mx-auto px-5 py-8">{children}</main>
    </div>
  );
}

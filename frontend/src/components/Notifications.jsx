import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { Bell, AlarmClock, AlertTriangle, CheckCheck } from "lucide-react";

const SEV = { retard: 3, j7: 2, j30: 1 };
const TYPE_STYLE = {
  j30: { icon: AlarmClock, cls: "text-blue-600" },
  j7: { icon: AlarmClock, cls: "text-amber-600" },
  retard: { icon: AlertTriangle, cls: "text-red-600" },
};

export function Notifications() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();

  const load = () => api.get("/notifications").then(({ data }) => setItems(data)).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 60000); return () => clearInterval(t); }, []);
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  // Regroupement par dossier : une entrée par dossier, rappel le plus urgent en tête.
  const groupsMap = items.reduce((acc, n) => {
    const g = acc[n.dossier_id] || (acc[n.dossier_id] = { dossier_id: n.dossier_id, dossier_nom: n.dossier_nom, list: [] });
    g.list.push(n);
    return acc;
  }, {});
  const groups = Object.values(groupsMap).map((g) => {
    const sorted = [...g.list].sort((a, b) => (SEV[b.type] || 0) - (SEV[a.type] || 0) || b.created_at.localeCompare(a.created_at));
    return { ...g, top: sorted[0], unread: g.list.filter((n) => !n.read).length };
  }).sort((a, b) => (SEV[b.top.type] || 0) - (SEV[a.top.type] || 0) || b.top.created_at.localeCompare(a.top.created_at));

  const unreadGroups = groups.filter((g) => g.unread > 0).length;

  const openGroup = async (g) => {
    setOpen(false);
    const unread = g.list.filter((n) => !n.read);
    if (unread.length) { try { await Promise.all(unread.map((n) => api.post(`/notifications/${n.id}/read`))); } catch (e) {} load(); }
    navigate(`/dossier/${g.dossier_id}`);
  };
  const markAll = async () => { try { await api.post("/notifications/read-all"); } catch (e) {} load(); };

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} data-testid="notifications-bell"
        className="relative flex h-9 w-9 items-center justify-center rounded-lg text-blue-100 hover:bg-white/10 transition-colors">
        <Bell size={18} />
        {unreadGroups > 0 && (
          <span data-testid="notifications-count" className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">{unreadGroups}</span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 rounded-xl border border-slate-200 bg-white shadow-xl z-50 overflow-hidden" data-testid="notifications-panel">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
            <span className="text-sm font-semibold text-[#0F2B48]">Rappels d'échéance</span>
            {unreadGroups > 0 && <button onClick={markAll} className="text-[11px] text-blue-600 hover:underline flex items-center gap-1" data-testid="notifications-markall"><CheckCheck size={12} /> Tout marquer lu</button>}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {groups.length === 0 && <div className="px-4 py-6 text-center text-sm text-slate-400">Aucun rappel pour le moment.</div>}
            {groups.map((g) => {
              const s = TYPE_STYLE[g.top.type] || TYPE_STYLE.j30;
              const Icon = s.icon;
              const hasUnread = g.unread > 0;
              return (
                <button key={g.dossier_id} onClick={() => openGroup(g)} data-testid={`notification-group-${g.dossier_id}`}
                  className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition-colors ${hasUnread ? "bg-blue-50/30" : "opacity-60"}`}>
                  <div className="flex items-start gap-2">
                    <Icon size={16} className={`mt-0.5 shrink-0 ${s.cls}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-semibold text-[#0F2B48] truncate">{g.dossier_nom}</p>
                        {g.list.length > 1 && <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-500">{g.list.length} rappels</span>}
                      </div>
                      <p className="text-xs text-slate-600 leading-snug mt-0.5">{g.top.message}</p>
                      <p className="text-[10px] text-slate-400 mt-1">{new Date(g.top.created_at).toLocaleDateString("fr-CA")}</p>
                    </div>
                    {hasUnread && <span className="ml-auto mt-1 h-2 w-2 rounded-full bg-blue-500 shrink-0" />}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

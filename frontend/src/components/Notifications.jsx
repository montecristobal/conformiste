import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { Bell, AlarmClock, AlertTriangle, CheckCheck } from "lucide-react";

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

  const unread = items.filter((i) => !i.read).length;
  const openItem = async (n) => {
    setOpen(false);
    if (!n.read) { try { await api.post(`/notifications/${n.id}/read`); } catch (e) {} load(); }
    navigate(`/dossier/${n.dossier_id}`);
  };
  const markAll = async () => { try { await api.post("/notifications/read-all"); } catch (e) {} load(); };

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} data-testid="notifications-bell"
        className="relative flex h-9 w-9 items-center justify-center rounded-lg text-blue-100 hover:bg-white/10 transition-colors">
        <Bell size={18} />
        {unread > 0 && (
          <span data-testid="notifications-count" className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">{unread}</span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 rounded-xl border border-slate-200 bg-white shadow-xl z-50 overflow-hidden" data-testid="notifications-panel">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
            <span className="text-sm font-semibold text-[#0F2B48]">Rappels d'échéance</span>
            {unread > 0 && <button onClick={markAll} className="text-[11px] text-blue-600 hover:underline flex items-center gap-1" data-testid="notifications-markall"><CheckCheck size={12} /> Tout marquer lu</button>}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {items.length === 0 && <div className="px-4 py-6 text-center text-sm text-slate-400">Aucun rappel pour le moment.</div>}
            {items.map((n) => {
              const s = TYPE_STYLE[n.type] || TYPE_STYLE.j30;
              const Icon = s.icon;
              return (
                <button key={n.id} onClick={() => openItem(n)} data-testid={`notification-${n.id}`}
                  className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition-colors ${n.read ? "opacity-60" : "bg-blue-50/30"}`}>
                  <div className="flex items-start gap-2">
                    <Icon size={16} className={`mt-0.5 shrink-0 ${s.cls}`} />
                    <div className="min-w-0">
                      <p className="text-xs text-slate-700 leading-snug">{n.message}</p>
                      <p className="text-[10px] text-slate-400 mt-1">{new Date(n.created_at).toLocaleDateString("fr-CA")}</p>
                    </div>
                    {!n.read && <span className="ml-auto mt-1 h-2 w-2 rounded-full bg-blue-500 shrink-0" />}
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

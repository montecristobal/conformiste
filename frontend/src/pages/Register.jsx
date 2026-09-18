import { useState } from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { formatApiError } from "@/lib/api";
import { ShieldCheck, User, Building2 } from "lucide-react";

export default function Register() {
  const location = useLocation();
  const [accountType, setAccountType] = useState(location.state?.account_type || "SOLO");
  const taille = location.state?.taille || null;
  const regimeA = taille === "moins_25";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await register({ name, email, password, account_type: accountType, taille });
      navigate("/dashboard");
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen paper-bg flex items-center justify-center px-5 py-10">
      <Card className="w-full max-w-md p-8">
        <Link to="/" className="flex items-center gap-2 mb-6" data-testid="register-brand-link">
          <ShieldCheck className="text-[#2563EB]" size={22} />
          <span className="font-display font-extrabold text-lg text-[#0F2B48]">CONFORMISTE</span>
        </Link>
        <h1 className="font-display text-2xl font-bold text-[#0F2B48]">Créer un compte</h1>
        <p className="text-sm text-slate-500 mb-5">Choisissez votre version, puis renseignez vos accès.</p>

        {taille && (
          <div className={`mb-5 rounded-xl border px-3 py-2 text-xs ${regimeA ? "bg-indigo-50 border-indigo-200 text-indigo-800" : "bg-blue-50 border-blue-200 text-blue-800"}`} data-testid="register-regime-note">
            {regimeA
              ? "Moins de 25 employés — régime des obligations universelles (aucun parcours de francisation)."
              : (taille === "100_plus" ? "100 employés et plus" : "Entre 25 et 99 employés") + " — parcours de francisation."}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 mb-5">
          {[["SOLO", User], ["PRO", Building2]].map(([m, Icon]) => (
            <button key={m} type="button" onClick={() => setAccountType(m)} data-testid={`register-mode-${m.toLowerCase()}`}
              className={`flex items-center gap-2 rounded-xl border-2 px-3 py-2.5 text-sm font-medium transition-colors ${
                accountType === m ? "border-[#2563EB] bg-blue-50 text-[#0F2B48]" : "border-slate-200 text-slate-500 hover:border-slate-300"
              }`}>
              <Icon size={18} /> Version {m}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Nom {accountType === "PRO" ? "du cabinet / consultant·e" : "de l'entreprise"}</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required data-testid="register-name-input" />
          </div>
          <div className="space-y-1.5">
            <Label>Courriel</Label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="register-email-input" />
          </div>
          <div className="space-y-1.5">
            <Label>Mot de passe (min. 6 caractères)</Label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} data-testid="register-password-input" />
          </div>
          {error && <p className="text-sm text-red-600" data-testid="register-error">{error}</p>}
          <Button type="submit" disabled={busy} data-testid="register-submit-button" className="w-full bg-[#0F2B48] hover:bg-[#0F2B48]/90">
            {busy ? "Création…" : `Créer mon compte ${accountType}`}
          </Button>
        </form>
        <p className="text-sm text-slate-500 mt-5 text-center">
          Déjà inscrit·e ?{" "}
          <Link to="/login" className="text-[#2563EB] font-medium hover:underline" data-testid="register-to-login-link">Se connecter</Link>
        </p>
      </Card>
    </div>
  );
}

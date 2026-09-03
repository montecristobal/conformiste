import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { formatApiError } from "@/lib/api";
import { ShieldCheck } from "lucide-react";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen paper-bg flex items-center justify-center px-5">
      <Card className="w-full max-w-md p-8">
        <Link to="/" className="flex items-center gap-2 mb-6" data-testid="login-brand-link">
          <ShieldCheck className="text-[#2563EB]" size={22} />
          <span className="font-display font-extrabold text-lg text-[#0F2B48]">CONFORMISTE</span>
        </Link>
        <h1 className="font-display text-2xl font-bold text-[#0F2B48]">Connexion</h1>
        <p className="text-sm text-slate-500 mb-6">Accédez à vos dossiers de francisation.</p>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Courriel</Label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="login-email-input" />
          </div>
          <div className="space-y-1.5">
            <Label>Mot de passe</Label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required data-testid="login-password-input" />
          </div>
          {error && <p className="text-sm text-red-600" data-testid="login-error">{error}</p>}
          <Button type="submit" disabled={busy} data-testid="login-submit-button" className="w-full bg-[#0F2B48] hover:bg-[#0F2B48]/90">
            {busy ? "Connexion…" : "Se connecter"}
          </Button>
        </form>
        <p className="text-sm text-slate-500 mt-5 text-center">
          Pas encore de compte ?{" "}
          <Link to="/register" className="text-[#2563EB] font-medium hover:underline" data-testid="login-to-register-link">Créer un compte</Link>
        </p>
      </Card>
    </div>
  );
}

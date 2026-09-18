import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import Welcome from "@/pages/Welcome";
import SizeGate from "@/pages/SizeGate";
import RegimeAIntro from "@/pages/RegimeAIntro";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Dashboard from "@/pages/Dashboard";
import ClientsPage from "@/pages/ClientsPage";
import DossierDetail from "@/pages/DossierDetail";
import MobileAmorce from "@/pages/MobileAmorce";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading || user === null) {
    return <div className="min-h-screen flex items-center justify-center text-slate-400">Chargement…</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function ProOnly({ children }) {
  const { user } = useAuth();
  if (user && user.account_type !== "PRO") return <Navigate to="/dashboard" replace />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<SizeGate />} />
          <Route path="/parcours-pme" element={<RegimeAIntro />} />
          <Route path="/welcome" element={<Welcome />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
          <Route path="/clients" element={<Protected><ProOnly><ClientsPage /></ProOnly></Protected>} />
          <Route path="/dossier/:id" element={<Protected><DossierDetail /></Protected>} />
          <Route path="/m/:sessionId" element={<MobileAmorce />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;

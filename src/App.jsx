import { useEffect, useState } from "react";
import { getToken, clearToken, getMe } from "./api";
import PublicApp from "./components/PublicApp";
import Overview from "./components/Overview";
import Datasets from "./components/Datasets";
import Jobs from "./components/Jobs";
import Deployments from "./components/Deployments";

const TABS = ["Overview", "Datasets", "Jobs", "Deployments"];

export default function App() {
  // If a token exists, we're "logged in". Login sets it; logout clears it.
  const [loggedIn, setLoggedIn] = useState(Boolean(getToken()));
  const [tab, setTab] = useState("Overview");
  const [email, setEmail] = useState("");

  // Fetch the current user's email for the header once logged in.
  useEffect(() => {
    if (loggedIn) {
      getMe()
        .then((u) => setEmail(u.email))
        .catch(() => setEmail(""));
    }
  }, [loggedIn]);

  if (!loggedIn) {
    return <PublicApp onLogin={() => setLoggedIn(true)} />;
  }

  function logout() {
    clearToken();
    setLoggedIn(false);
    setEmail("");
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      {/* Header */}
      <header className="flex items-center justify-between bg-slate-900 px-6 py-4 text-white">
        <h1 className="text-xl font-bold">
          Model<span className="text-emerald-400">Forge</span>
        </h1>
        <div className="flex items-center gap-4">
          {email && <span className="text-sm text-slate-300">{email}</span>}
          <button
            onClick={logout}
            className="rounded bg-slate-700 px-3 py-1 text-sm hover:bg-slate-600"
          >
            Log out
          </button>
        </div>
      </header>

      {/* Tabs */}
      <nav className="flex gap-1 border-b bg-white px-6">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-3 text-sm font-medium ${
              tab === t
                ? "border-b-2 border-emerald-500 text-emerald-600"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </nav>

      {/* Active section */}
      <main className="mx-auto max-w-4xl p-6">
        {tab === "Overview" && <Overview />}
        {tab === "Datasets" && <Datasets />}
        {tab === "Jobs" && <Jobs />}
        {tab === "Deployments" && <Deployments />}
      </main>
    </div>
  );
}

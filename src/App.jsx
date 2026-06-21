import { useState } from "react";
import { getToken, clearToken } from "./api";
import Login from "./components/Login";
import Datasets from "./components/Datasets";
import Jobs from "./components/Jobs";
import Deployments from "./components/Deployments";

const TABS = ["Datasets", "Jobs", "Deployments"];

export default function App() {
  // If a token exists, we're "logged in". Login sets it; logout clears it.
  const [loggedIn, setLoggedIn] = useState(Boolean(getToken()));
  const [tab, setTab] = useState("Datasets");

  if (!loggedIn) {
    return <Login onLogin={() => setLoggedIn(true)} />;
  }

  function logout() {
    clearToken();
    setLoggedIn(false);
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      {/* Header */}
      <header className="flex items-center justify-between bg-slate-900 px-6 py-4 text-white">
        <h1 className="text-xl font-bold">
          Model<span className="text-emerald-400">Forge</span>
        </h1>
        <button
          onClick={logout}
          className="rounded bg-slate-700 px-3 py-1 text-sm hover:bg-slate-600"
        >
          Log out
        </button>
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
        {tab === "Datasets" && <Datasets />}
        {tab === "Jobs" && <Jobs />}
        {tab === "Deployments" && <Deployments />}
      </main>
    </div>
  );
}

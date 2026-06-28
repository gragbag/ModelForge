import { useState } from "react";
import Login from "./Login";

// The unauthenticated experience: a top navbar + a landing page + the auth form.
// `view` switches between the landing page and the login/register form.
export default function PublicApp({ onLogin }) {
  const [view, setView] = useState("home"); // "home" | "login" | "register"

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Top navbar */}
      <header className="flex items-center justify-between bg-slate-900 px-6 py-4 text-white">
        <button
          onClick={() => setView("home")}
          className="text-xl font-bold tracking-tight"
        >
          Model<span className="text-emerald-400">Forge</span>
        </button>
        <nav className="flex items-center gap-2">
          <button
            onClick={() => setView("home")}
            className="rounded px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700 hover:text-white"
          >
            Home
          </button>
          <button
            onClick={() => setView("login")}
            className="rounded px-3 py-1.5 text-sm hover:bg-slate-700"
          >
            Login
          </button>
          <button
            onClick={() => setView("register")}
            className="rounded bg-emerald-500 px-3 py-1.5 text-sm font-medium hover:bg-emerald-600"
          >
            Sign up
          </button>
        </nav>
      </header>

      {/* Body */}
      {view === "home" ? (
        <Home onGetStarted={() => setView("register")} />
      ) : (
        <Login mode={view} onLogin={onLogin} onSwitchMode={setView} />
      )}
    </div>
  );
}

function Home({ onGetStarted }) {
  return (
    <main className="mx-auto max-w-4xl px-6 py-20">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-slate-100 sm:text-5xl">
          Train, track, and serve ML models.
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-300">
          ModelForge is a cloud-native MLOps platform — upload a dataset, train a
          model in the background, and deploy it as a live prediction endpoint.
        </p>
        <button
          onClick={onGetStarted}
          className="mt-8 rounded-lg bg-emerald-500 px-6 py-3 font-medium text-white shadow hover:bg-emerald-600"
        >
          Get started
        </button>
      </div>

      <div className="mt-20 grid gap-6 sm:grid-cols-3">
        <FeatureCard
          title="Upload"
          desc="Upload CSV datasets; metadata is stored and the file lands in object storage."
        />
        <FeatureCard
          title="Train"
          desc="Submit a training job and a background worker trains a model, tracked in MLflow."
        />
        <FeatureCard
          title="Serve"
          desc="Deploy a registered model version and get predictions on new data via REST."
        />
      </div>
    </main>
  );
}

function FeatureCard({ title, desc }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800 p-6 transition hover:border-slate-600">
      <h3 className="font-semibold text-emerald-400">{title}</h3>
      <p className="mt-2 text-sm text-slate-300">{desc}</p>
    </div>
  );
}

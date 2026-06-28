import { useEffect, useState } from "react";
import { listDatasets, listJobs, listDeployments } from "../api";
import { headingClass } from "../ui";

export default function Overview() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    // Fetch all three lists in parallel and derive the counts.
    Promise.all([listDatasets(), listJobs(), listDeployments()])
      .then(([datasets, jobs, deployments]) => {
        setStats({
          datasets: datasets.length,
          jobs: jobs.length,
          completed: jobs.filter((j) => j.status === "completed").length,
          deployments: deployments.length,
        });
      })
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <p className="text-sm text-red-400">{error}</p>;
  if (!stats) return <p className="text-sm text-slate-400">Loading…</p>;

  const cards = [
    { label: "Datasets", value: stats.datasets },
    { label: "Jobs", value: stats.jobs },
    { label: "Trained models", value: stats.completed },
    { label: "Deployments", value: stats.deployments },
  ];

  return (
    <section>
      <h2 className={headingClass}>Overview</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <div
            key={c.label}
            className="rounded-xl border border-slate-700 bg-slate-800 p-5 transition hover:border-slate-600"
          >
            <p className="text-4xl font-bold text-emerald-400">{c.value}</p>
            <p className="mt-2 text-xs font-medium uppercase tracking-wide text-slate-400">
              {c.label}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

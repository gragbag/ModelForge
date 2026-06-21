import { useEffect, useState } from "react";
import { listJobs, createJob, listDatasets } from "../api";

const STATUS_COLORS = {
  queued: "bg-slate-200 text-slate-700",
  running: "bg-blue-200 text-blue-800",
  completed: "bg-emerald-200 text-emerald-800",
  failed: "bg-red-200 text-red-800",
};

export default function Jobs() {
  const [jobs, setJobs] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [error, setError] = useState("");
  // Form state
  const [datasetId, setDatasetId] = useState("");
  const [targetColumn, setTargetColumn] = useState("");
  const [taskType, setTaskType] = useState("classification");

  async function refresh() {
    try {
      setJobs(await listJobs());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh();
    listDatasets().then(setDatasets).catch(() => {});
    // Poll every 3s so QUEUED → RUNNING → COMPLETED updates live.
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await createJob({
        dataset_id: Number(datasetId),
        model_type: "random_forest",
        target_column: targetColumn,
        task_type: taskType,
      });
      setTargetColumn("");
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold">Jobs</h2>

      {/* Submit a training job */}
      <form
        onSubmit={handleSubmit}
        className="mb-6 flex flex-wrap items-end gap-3 rounded border bg-white p-4"
      >
        <div>
          <label className="block text-xs text-slate-500">Dataset</label>
          <select
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
            required
            className="rounded border px-2 py-1 text-sm"
          >
            <option value="">Select…</option>
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                #{d.id} {d.filename}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-500">Target column</label>
          <input
            value={targetColumn}
            onChange={(e) => setTargetColumn(e.target.value)}
            required
            placeholder="e.g. passed"
            className="rounded border px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500">Task</label>
          <select
            value={taskType}
            onChange={(e) => setTaskType(e.target.value)}
            className="rounded border px-2 py-1 text-sm"
          >
            <option value="classification">classification</option>
            <option value="regression">regression</option>
          </select>
        </div>
        <button
          type="submit"
          className="rounded bg-emerald-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-600"
        >
          Train
        </button>
      </form>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      <table className="w-full overflow-hidden rounded border bg-white text-sm">
        <thead className="bg-slate-100 text-left text-slate-600">
          <tr>
            <th className="p-2">ID</th>
            <th className="p-2">Status</th>
            <th className="p-2">Target</th>
            <th className="p-2">Metrics</th>
          </tr>
        </thead>
        <tbody>
          {jobs.length === 0 ? (
            <tr>
              <td colSpan="4" className="p-4 text-center text-slate-400">
                No jobs yet.
              </td>
            </tr>
          ) : (
            jobs.map((j) => (
              <tr key={j.id} className="border-t">
                <td className="p-2">{j.id}</td>
                <td className="p-2">
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${
                      STATUS_COLORS[j.status] || ""
                    }`}
                  >
                    {j.status}
                  </span>
                </td>
                <td className="p-2">{j.target_column}</td>
                <td className="p-2 font-mono text-xs">
                  {j.metrics
                    ? Object.entries(j.metrics)
                        .map(([k, v]) => `${k}=${Number(v).toFixed(3)}`)
                        .join("  ")
                    : "—"}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </section>
  );
}

import { useEffect, useState } from "react";
import {
  listDeployments,
  createDeployment,
  deleteDeployment,
  listModelVersions,
  predict,
  predictCsv,
} from "../api";

export default function Deployments() {
  const [deployments, setDeployments] = useState([]);
  const [versions, setVersions] = useState([]); // available registered models
  const [error, setError] = useState("");
  // Create-deployment form: index of the chosen model in `versions`
  const [selectedIdx, setSelectedIdx] = useState(0);
  // Predict form
  const [selectedId, setSelectedId] = useState("");
  const [mode, setMode] = useState("json"); // "json" | "csv"
  const [featuresJson, setFeaturesJson] = useState(
    '{\n  "hours_studied": 8,\n  "prev_score": 80,\n  "attendance": 95\n}'
  );
  // Results: { rows: [...], predictions: [...] }
  const [result, setResult] = useState(null);

  async function refresh() {
    try {
      setDeployments(await listDeployments());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh();
    // Load the registered model versions for the deploy dropdown.
    listModelVersions()
      .then((vs) => {
        setVersions(vs);
        setSelectedIdx(0);
      })
      .catch(() => {});
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    const model = versions[selectedIdx];
    if (!model) {
      setError("No model selected");
      return;
    }
    try {
      await createDeployment({
        model_name: model.name,
        model_version: model.version,
      });
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    setError("");
    try {
      await deleteDeployment(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  // Predict from the JSON box (accepts a single object OR an array of rows).
  async function handlePredictJson(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    if (!selectedId) {
      setError("Select a deployment first");
      return;
    }
    try {
      const parsed = JSON.parse(featuresJson);
      const rows = Array.isArray(parsed) ? parsed : [parsed]; // single -> batch of 1
      const res = await predict(Number(selectedId), rows);
      setResult(res);
    } catch (err) {
      setError(err.message);
    }
  }

  // Predict from an uploaded CSV (one prediction per row).
  async function handlePredictCsv(e) {
    const file = e.target.files[0];
    if (!file) return;
    setError("");
    setResult(null);
    if (!selectedId) {
      setError("Select a deployment first");
      e.target.value = "";
      return;
    }
    try {
      const res = await predictCsv(Number(selectedId), file);
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      e.target.value = "";
    }
  }

  return (
    <section className="space-y-6">
      <h2 className="text-lg font-semibold">Deployments</h2>

      {/* Create a deployment */}
      <form
        onSubmit={handleCreate}
        className="flex items-end gap-3 rounded border bg-white p-4"
      >
        <div>
          <label className="block text-xs text-slate-500">Model</label>
          <select
            value={selectedIdx}
            onChange={(e) => setSelectedIdx(Number(e.target.value))}
            required
            className="rounded border px-2 py-1 text-sm"
          >
            {versions.length === 0 ? (
              <option value="">No models — train one first</option>
            ) : (
              versions.map((v, i) => (
                <option key={`${v.name}-${v.version}`} value={i}>
                  {v.name} (v{v.version})
                  {v.stage && v.stage !== "None" ? ` · ${v.stage}` : ""}
                </option>
              ))
            )}
          </select>
        </div>
        <button
          type="submit"
          disabled={versions.length === 0}
          className="rounded bg-emerald-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-50"
        >
          Deploy
        </button>
      </form>

      {/* Deployment list */}
      <table className="w-full overflow-hidden rounded border bg-white text-sm">
        <thead className="bg-slate-100 text-left text-slate-600">
          <tr>
            <th className="p-2">ID</th>
            <th className="p-2">Model</th>
            <th className="p-2">Version</th>
            <th className="p-2"></th>
          </tr>
        </thead>
        <tbody>
          {deployments.length === 0 ? (
            <tr>
              <td colSpan="4" className="p-4 text-center text-slate-400">
                No deployments yet.
              </td>
            </tr>
          ) : (
            deployments.map((d) => (
              <tr key={d.id} className="border-t">
                <td className="p-2">{d.id}</td>
                <td className="p-2">{d.model_name}</td>
                <td className="p-2">{d.model_version}</td>
                <td className="p-2 text-right">
                  <button
                    onClick={() => handleDelete(d.id)}
                    className="rounded border border-red-300 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* Predict */}
      <div className="rounded border bg-white p-4">
        <h3 className="mb-3 font-medium">Get predictions</h3>

        {/* Deployment selector (shared by both modes) */}
        <div className="mb-3">
          <label className="block text-xs text-slate-500">Deployment</label>
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="rounded border px-2 py-1 text-sm"
          >
            <option value="">Select…</option>
            {deployments.map((d) => (
              <option key={d.id} value={d.id}>
                #{d.id} {d.model_name} v{d.model_version}
              </option>
            ))}
          </select>
        </div>

        {/* Input mode toggle */}
        <div className="mb-3 flex gap-4 border-b text-sm">
          {["json", "csv"].map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`pb-2 ${
                mode === m
                  ? "border-b-2 border-emerald-500 font-medium text-emerald-600"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              {m === "json" ? "Enter rows (JSON)" : "Upload CSV"}
            </button>
          ))}
        </div>

        {mode === "json" ? (
          <form onSubmit={handlePredictJson}>
            <p className="mb-1 text-xs text-slate-500">
              A single row {"{...}"} or an array of rows [...]. Columns = the
              model's features (no target).
            </p>
            <textarea
              value={featuresJson}
              onChange={(e) => setFeaturesJson(e.target.value)}
              rows={6}
              className="mb-3 w-full rounded border p-2 font-mono text-xs"
            />
            <button
              type="submit"
              className="rounded bg-emerald-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-600"
            >
              Predict
            </button>
          </form>
        ) : (
          <div>
            <p className="mb-2 text-xs text-slate-500">
              Upload a CSV of feature rows (columns = the model's features, no
              target column). One prediction per row.
            </p>
            <label className="cursor-pointer rounded bg-emerald-500 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-600">
              Choose CSV
              <input type="file" accept=".csv" onChange={handlePredictCsv} className="hidden" />
            </label>
          </div>
        )}

        {/* Results: each input row + its prediction */}
        {result && result.rows.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <p className="mb-2 text-xs font-medium text-slate-500">
              {result.predictions.length} prediction(s)
            </p>
            <table className="text-xs">
              <thead>
                <tr className="text-left text-slate-500">
                  {Object.keys(result.rows[0]).map((c) => (
                    <th key={c} className="border-b px-2 py-1">
                      {c}
                    </th>
                  ))}
                  <th className="border-b px-2 py-1 text-emerald-600">prediction</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, i) => (
                  <tr key={i}>
                    {Object.keys(result.rows[0]).map((c) => (
                      <td key={c} className="border-b px-2 py-1">
                        {String(row[c])}
                      </td>
                    ))}
                    <td className="border-b px-2 py-1 font-bold text-emerald-700">
                      {String(result.predictions[i])}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
    </section>
  );
}

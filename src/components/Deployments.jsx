import { useEffect, useState } from "react";
import {
  listDeployments,
  createDeployment,
  deleteDeployment,
  listModelVersions,
  predict,
  predictCsv,
} from "../api";
import {
  btnDanger,
  btnPrimary,
  cardClass,
  inputClass,
  labelClass,
  rowClass,
  tableClass,
  tableWrap,
  tdClass,
  theadClass,
  thClass,
} from "../ui";

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
      <form onSubmit={handleCreate} className={`flex items-end gap-3 ${cardClass}`}>
        <div className="flex-1">
          <label className={labelClass}>Model</label>
          <select
            value={selectedIdx}
            onChange={(e) => setSelectedIdx(Number(e.target.value))}
            required
            className={inputClass}
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
        <button type="submit" disabled={versions.length === 0} className={btnPrimary}>
          Deploy
        </button>
      </form>

      {/* Deployment list */}
      <div className={tableWrap}>
        <table className={tableClass}>
          <thead className={theadClass}>
            <tr>
              <th className={thClass}>ID</th>
              <th className={thClass}>Model</th>
              <th className={thClass}>Version</th>
              <th className={thClass}></th>
            </tr>
          </thead>
          <tbody>
            {deployments.length === 0 ? (
              <tr>
                <td colSpan="4" className="px-4 py-10 text-center text-slate-400">
                  No deployments yet.
                </td>
              </tr>
            ) : (
              deployments.map((d) => (
                <tr key={d.id} className={rowClass}>
                  <td className={`${tdClass} text-slate-400`}>{d.id}</td>
                  <td className={`${tdClass} font-medium`}>{d.model_name}</td>
                  <td className={`${tdClass} text-slate-300`}>{d.model_version}</td>
                  <td className={`${tdClass} text-right`}>
                    <button onClick={() => handleDelete(d.id)} className={btnDanger}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Predict */}
      <div className={cardClass}>
        <h3 className="mb-4 font-semibold">Get predictions</h3>

        {/* Deployment selector (shared by both modes) */}
        <div className="mb-4">
          <label className={labelClass}>Deployment</label>
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className={inputClass}
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
        <div className="mb-4 flex gap-4 border-b border-slate-700 text-sm">
          {["json", "csv"].map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`pb-2 transition ${
                mode === m
                  ? "border-b-2 border-emerald-500 font-medium text-emerald-400"
                  : "text-slate-400 hover:text-slate-100"
              }`}
            >
              {m === "json" ? "Enter rows (JSON)" : "Upload CSV"}
            </button>
          ))}
        </div>

        {mode === "json" ? (
          <form onSubmit={handlePredictJson}>
            <p className="mb-2 text-xs text-slate-400">
              A single row {"{...}"} or an array of rows [...]. Columns = the
              model's features (no target).
            </p>
            <textarea
              value={featuresJson}
              onChange={(e) => setFeaturesJson(e.target.value)}
              rows={6}
              className={`mb-3 font-mono ${inputClass}`}
            />
            <button type="submit" className={btnPrimary}>
              Predict
            </button>
          </form>
        ) : (
          <div>
            <p className="mb-2 text-xs text-slate-400">
              Upload a CSV of feature rows (columns = the model's features, no
              target column). One prediction per row.
            </p>
            <label className={`cursor-pointer ${btnPrimary}`}>
              Choose CSV
              <input type="file" accept=".csv" onChange={handlePredictCsv} className="hidden" />
            </label>
          </div>
        )}

        {/* Results: each input row + its prediction */}
        {result && result.rows.length > 0 && (
          <div className="mt-5 overflow-x-auto">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
              {result.predictions.length} prediction(s)
            </p>
            <table className="text-xs">
              <thead>
                <tr className="text-left text-slate-400">
                  {Object.keys(result.rows[0]).map((c) => (
                    <th
                      key={c}
                      className="border-b border-slate-700 px-3 py-1.5 font-medium"
                    >
                      {c}
                    </th>
                  ))}
                  <th className="border-b border-slate-700 px-3 py-1.5 font-medium text-emerald-400">
                    prediction
                  </th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, i) => (
                  <tr key={i}>
                    {Object.keys(result.rows[0]).map((c) => (
                      <td
                        key={c}
                        className="border-b border-slate-800 px-3 py-1.5 text-slate-300"
                      >
                        {String(row[c])}
                      </td>
                    ))}
                    <td className="border-b border-slate-800 px-3 py-1.5 font-bold text-emerald-400">
                      {String(result.predictions[i])}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}
    </section>
  );
}

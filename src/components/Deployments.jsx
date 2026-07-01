import { useEffect, useState } from "react";
import {
  listDeployments,
  createDeployment,
  deleteDeployment,
  listModelVersions,
  deleteModelVersion,
  predict,
  predictCsv,
  predictImage,
} from "../api";
import { btnDanger, cardClass, inputClass } from "../ui";

const BADGE = "rounded bg-slate-700 px-1.5 py-0.5 text-xs uppercase tracking-wide text-slate-300";
const deployBtn =
  "rounded-lg bg-emerald-500 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-emerald-600";

function metricsLine(metrics) {
  const entries = Object.entries(metrics || {});
  return entries.length
    ? entries.map(([k, v]) => `${k}=${Number(v).toFixed(3)}`).join("  ")
    : null;
}
function parseHyper(params) {
  try {
    return JSON.parse(params?.hyperparameters || "{}");
  } catch {
    return {};
  }
}

export default function Deployments() {
  const [deployments, setDeployments] = useState([]);
  const [versions, setVersions] = useState([]); // registered models (from MLflow)
  const [error, setError] = useState("");
  const [view, setView] = useState("deploy"); // "deploy" | "inference"
  const [query, setQuery] = useState("");
  // Predict panel
  const [selectedId, setSelectedId] = useState("");
  const [mode, setMode] = useState("json"); // "json" | "csv"
  const [featuresJson, setFeaturesJson] = useState(
    '{\n  "hours_studied": 8,\n  "prev_score": 80,\n  "attendance": 95\n}'
  );
  const [result, setResult] = useState(null);
  const [imagePreview, setImagePreview] = useState("");
  const [imageResult, setImageResult] = useState(null);

  const selectedDeployment = deployments.find((d) => d.id === Number(selectedId));
  const isImageDeployment = selectedDeployment?.modality === "image";

  async function refresh() {
    try {
      setDeployments(await listDeployments());
    } catch (err) {
      setError(err.message);
    }
  }
  async function refreshModels() {
    try {
      setVersions(await listModelVersions());
    } catch {
      /* best-effort */
    }
  }
  useEffect(() => {
    refresh();
    refreshModels();
  }, []);

  async function handleDeploy(model) {
    setError("");
    try {
      await createDeployment({ model_name: model.name, model_version: model.version });
      await refresh();
      setView("inference"); // jump to where you'll use it
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteModel(model) {
    if (!window.confirm(`Delete ${model.name} v${model.version} from the registry?`))
      return;
    setError("");
    try {
      await deleteModelVersion(model.name, model.version);
      await refreshModels();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteDeployment(id) {
    setError("");
    try {
      await deleteDeployment(id);
      if (Number(selectedId) === id) setSelectedId("");
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  function selectForPredict(id) {
    setSelectedId(String(id));
    setResult(null);
    setImageResult(null);
    setImagePreview("");
    setError("");
  }

  async function handlePredictJson(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    try {
      const parsed = JSON.parse(featuresJson);
      const rows = Array.isArray(parsed) ? parsed : [parsed];
      setResult(await predict(Number(selectedId), rows));
    } catch (err) {
      setError(err.message);
    }
  }
  async function handlePredictCsv(e) {
    const file = e.target.files[0];
    if (!file) return;
    setError("");
    setResult(null);
    try {
      setResult(await predictCsv(Number(selectedId), file));
    } catch (err) {
      setError(err.message);
    } finally {
      e.target.value = "";
    }
  }
  async function handlePredictImage(e) {
    const file = e.target.files[0];
    if (!file) return;
    setError("");
    setImageResult(null);
    setImagePreview(URL.createObjectURL(file));
    try {
      setImageResult(await predictImage(Number(selectedId), file));
    } catch (err) {
      setError(err.message);
    } finally {
      e.target.value = "";
    }
  }

  const q = query.trim().toLowerCase();
  const filteredModels = versions.filter((v) => {
    if (!q) return true;
    const p = v.params || {};
    return [v.name, p.model_type, p.dataset, p.task_type].some((s) =>
      (s || "").toLowerCase().includes(q)
    );
  });

  return (
    <section>
      <div className="mb-6 inline-flex rounded-lg border border-slate-700 bg-slate-800 p-1">
        {[
          ["deploy", "Deploy"],
          ["inference", "Inference"],
        ].map(([key, label]) => (
          <button
            key={key}
            onClick={() => setView(key)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
              view === key
                ? "bg-emerald-500 text-white"
                : "text-slate-400 hover:text-slate-100"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      {view === "deploy" ? (
        /* ---------------- Deploy: registered model cards ---------------- */
        <>
          <p className="mb-4 text-xs text-slate-400">
            Trained models from the registry. Deploy one to serve predictions.
          </p>
          <div className="relative mb-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m21 21-4.3-4.3m0 0A7.5 7.5 0 1 0 5.6 5.6a7.5 7.5 0 0 0 10.6 10.6Z"
              />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search models…"
              className="w-full rounded-lg border border-slate-600 bg-slate-700 py-2 pl-9 pr-3 text-sm text-slate-100 transition focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
            />
          </div>

          <div className="space-y-3">
            {filteredModels.length === 0 ? (
              <p className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-10 text-center text-slate-400">
                {versions.length === 0
                  ? "No models yet — train one in the Jobs tab."
                  : `No models match “${query}”.`}
              </p>
            ) : (
              filteredModels.map((v) => {
                const p = v.params || {};
                const hp = parseHyper(p);
                const ml = metricsLine(v.metrics);
                return (
                  <div
                    key={`${v.name}-${v.version}`}
                    className="rounded-xl border border-slate-700 bg-slate-800 p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-medium">
                          {v.name}{" "}
                          <span className="text-xs text-slate-500">v{v.version}</span>
                        </div>
                        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-400">
                          {p.model_type && (
                            <span>
                              model:{" "}
                              <span className="text-slate-300">{p.model_type}</span>
                            </span>
                          )}
                          {p.task_type && (
                            <span>
                              task:{" "}
                              <span className="text-slate-300">{p.task_type}</span>
                            </span>
                          )}
                          {p.dataset && (
                            <span>
                              dataset:{" "}
                              <span className="text-slate-300">{p.dataset}</span>
                            </span>
                          )}
                        </div>
                        {ml && (
                          <div className="mt-1 font-mono text-xs text-emerald-300">
                            {ml}
                          </div>
                        )}
                        {Object.keys(hp).length > 0 && (
                          <div className="mt-1 truncate text-xs text-slate-500">
                            {Object.entries(hp)
                              .map(([k, val]) => `${k}=${val}`)
                              .join("  ")}
                          </div>
                        )}
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <button onClick={() => handleDeploy(v)} className={deployBtn}>
                          Deploy
                        </button>
                        <button
                          onClick={() => handleDeleteModel(v)}
                          className={btnDanger}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </>
      ) : (
        /* ---------------- Inference: deployments + predict ---------------- */
        <>
          <div className="space-y-3">
            {deployments.length === 0 ? (
              <p className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-10 text-center text-slate-400">
                No deployments yet — deploy a model from the Deploy tab.
              </p>
            ) : (
              deployments.map((d) => {
                const v = versions.find(
                  (x) =>
                    x.name === d.model_name &&
                    String(x.version) === String(d.model_version)
                );
                const p = v?.params || {};
                const selected = Number(selectedId) === d.id;
                return (
                  <div
                    key={d.id}
                    onClick={() => selectForPredict(d.id)}
                    className={`cursor-pointer rounded-xl border p-4 transition ${
                      selected
                        ? "border-emerald-500 bg-emerald-500/5 ring-1 ring-emerald-500"
                        : "border-slate-700 bg-slate-800 hover:border-slate-600"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-medium">
                          {d.model_name}{" "}
                          <span className="text-xs text-slate-500">
                            v{d.model_version}
                          </span>
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
                          <span className={BADGE}>{d.modality}</span>
                          {p.model_type && (
                            <span>
                              model:{" "}
                              <span className="text-slate-300">{p.model_type}</span>
                            </span>
                          )}
                          {p.dataset && (
                            <span>
                              dataset:{" "}
                              <span className="text-slate-300">{p.dataset}</span>
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-3">
                        {selected && (
                          <span className="text-xs text-emerald-400">selected</span>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteDeployment(d.id);
                          }}
                          className={btnDanger}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Predict panel for the selected deployment */}
          <div className={`mt-6 ${cardClass}`}>
            <h3 className="mb-4 font-semibold">Predict</h3>
            {!selectedDeployment ? (
              <p className="text-sm text-slate-400">
                Select a deployment above to run predictions.
              </p>
            ) : isImageDeployment ? (
              <div>
                <p className="mb-2 text-xs text-slate-400">
                  Upload an image to classify with this model.
                </p>
                <label className={`cursor-pointer ${deployBtn}`}>
                  Choose image
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handlePredictImage}
                    className="hidden"
                  />
                </label>
                {imagePreview && (
                  <div className="mt-4 flex items-center gap-4">
                    <img
                      src={imagePreview}
                      alt="uploaded"
                      className="h-24 w-24 rounded-lg border border-slate-700 object-cover"
                    />
                    {imageResult && (
                      <div>
                        <p className="text-xl font-semibold text-emerald-400">
                          {imageResult.prediction}
                        </p>
                        <p className="text-xs text-slate-400">
                          {(imageResult.confidence * 100).toFixed(1)}% confidence
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <>
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
                    <button type="submit" className={deployBtn}>
                      Predict
                    </button>
                  </form>
                ) : (
                  <div>
                    <p className="mb-2 text-xs text-slate-400">
                      Upload a CSV of feature rows (no target column). One prediction
                      per row.
                    </p>
                    <label className={`cursor-pointer ${deployBtn}`}>
                      Choose CSV
                      <input
                        type="file"
                        accept=".csv"
                        onChange={handlePredictCsv}
                        className="hidden"
                      />
                    </label>
                  </div>
                )}

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
              </>
            )}
          </div>
        </>
      )}
    </section>
  );
}

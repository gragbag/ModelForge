import { useEffect, useState } from "react";
import {
  listJobs,
  createJob,
  listDatasets,
  deleteJob,
  getDatasetPreview,
  listModelTypes,
} from "../api";
import Combobox from "./Combobox";
import { btnPrimary, inputClass, labelClass } from "../ui";

const STATUS_COLORS = {
  queued: "bg-slate-700 text-slate-200",
  running: "bg-blue-500/20 text-blue-300",
  completed: "bg-emerald-500/20 text-emerald-300",
  failed: "bg-red-500/20 text-red-300",
};

// Display metadata for the model picker cards. The backend owns which models
// exist + their hyperparameters; this just decorates each name for the UI.
const MODEL_META = {
  random_forest: {
    label: "Random Forest",
    family: "Ensemble",
    desc: "Robust ensemble of trees — a strong default.",
    recommended: true,
  },
  gradient_boosting: {
    label: "Gradient Boosting",
    family: "Ensemble",
    desc: "Sequential trees; often top accuracy on tabular data.",
  },
  decision_tree: {
    label: "Decision Tree",
    family: "Tree",
    desc: "A single, interpretable decision tree.",
  },
  linear: {
    label: "Linear",
    family: "Linear",
    desc: "Fast, simple baseline (logistic / linear).",
  },
  svm: {
    label: "SVM",
    family: "Kernel",
    desc: "Maximal-margin boundaries; great on small data.",
  },
  knn: {
    label: "KNN",
    family: "Instance",
    desc: "Predicts from the nearest training points.",
  },
  mlp: {
    label: "MLP",
    family: "Neural",
    desc: "Feedforward neural network.",
  },
  cnn: {
    label: "CNN",
    family: "Neural",
    desc: "Convolutional network — the model for image data.",
    recommended: true,
  },
};

export default function Jobs() {
  const [jobs, setJobs] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [error, setError] = useState("");
  const [models, setModels] = useState([]); // [{ name, params: [...] }]
  const [view, setView] = useState("train"); // "train" | "models"
  // Form state
  const [name, setName] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [columns, setColumns] = useState([]); // columns of the selected dataset
  const [targetColumn, setTargetColumn] = useState("");
  const [taskType, setTaskType] = useState("classification");
  const [modelType, setModelType] = useState("random_forest");
  const [scaleFeatures, setScaleFeatures] = useState(false);
  const [hyperparams, setHyperparams] = useState({}); // { paramName: value }
  const [modelQuery, setModelQuery] = useState(""); // filters the model cards
  const [description, setDescription] = useState("");
  const [step, setStep] = useState(0); // wizard step index

  // The modality of the chosen dataset drives the whole form (which models,
  // whether a target column / task / scaling apply).
  const selectedDataset = datasets.find((d) => d.id === Number(datasetId));
  const modality = selectedDataset?.modality ?? "tabular";
  const isImage = modality === "image";

  // The params (hyperparameter specs) of the currently-selected model.
  const currentParams = models.find((m) => m.name === modelType)?.params || [];

  // Model cards matching the search box (by name, label, family, or description).
  const q = modelQuery.trim().toLowerCase();
  const filteredModels = models.filter((m) => {
    if (!q) return true;
    const meta = MODEL_META[m.name] || {};
    return [m.name, meta.label, meta.family, meta.desc]
      .some((s) => (s || "").toLowerCase().includes(q));
  });

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

  // Load the models for the selected dataset's modality (tabular models vs the
  // image CNN), and default the selection to the first one.
  useEffect(() => {
    listModelTypes(modality)
      .then((m) => {
        setModels(m);
        setModelType(m[0]?.name ?? "");
      })
      .catch(() => {});
  }, [modality]);

  // When the model changes (or specs load), reset hyperparameters to its defaults.
  useEffect(() => {
    const spec = models.find((m) => m.name === modelType);
    if (spec) {
      const defaults = {};
      spec.params.forEach((p) => {
        defaults[p.name] = p.default;
      });
      setHyperparams(defaults);
    }
  }, [modelType, models]);

  // When the selected dataset changes, fetch its columns and default the target
  // to the LAST column (the target variable in most ML datasets).
  useEffect(() => {
    // Image datasets have no columns/target — skip the preview fetch for them.
    if (!datasetId || isImage) {
      setColumns([]);
      setTargetColumn("");
      return;
    }
    getDatasetPreview(datasetId)
      .then((p) => {
        setColumns(p.columns || []);
        setTargetColumn(p.columns?.[p.columns.length - 1] || "");
      })
      .catch(() => setColumns([]));
  }, [datasetId, isImage]);

  async function handleSubmit(e) {
    e?.preventDefault();
    setError("");
    try {
      // Image jobs have no target column/scaling and are always classification;
      // tabular jobs carry the full set of fields.
      const common = {
        name,
        description,
        dataset_id: Number(datasetId),
        model_type: modelType,
        hyperparameters: hyperparams,
      };
      const payload = isImage
        ? { ...common, task_type: "classification" }
        : {
            ...common,
            target_column: targetColumn,
            task_type: taskType,
            scale_features: scaleFeatures,
          };
      await createJob(payload);
      await refresh();
      setStep(0); // reset the wizard for the next job
      setView("models"); // jump to the list so the user watches it train
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    setError("");
    try {
      await deleteJob(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  function setParam(nameKey, val) {
    setHyperparams((h) => ({ ...h, [nameKey]: val }));
  }

  // Wizard steps — image datasets skip the target/task step.
  const stepDefs = isImage
    ? [
        { key: "dataset", label: "Dataset", hint: "Which dataset do you want to train on?" },
        { key: "model", label: "Model", hint: "Choose a model for this image dataset." },
        { key: "tune", label: "Tune", hint: "Adjust the hyperparameters (optional)." },
        { key: "details", label: "Details", hint: "Name your model and add any notes." },
      ]
    : [
        { key: "dataset", label: "Dataset", hint: "Which dataset do you want to train on?" },
        { key: "target", label: "Target", hint: "Pick the column to predict and the problem type." },
        { key: "model", label: "Model", hint: "Choose a model to train." },
        { key: "tune", label: "Tune", hint: "Adjust the hyperparameters (optional)." },
        { key: "details", label: "Details", hint: "Name your model and add any notes." },
      ];
  const current = stepDefs[Math.min(step, stepDefs.length - 1)];
  const isLastStep = step >= stepDefs.length - 1;

  function stepValid(key) {
    if (key === "dataset") return Boolean(datasetId);
    if (key === "target") return Boolean(targetColumn);
    if (key === "model") return Boolean(modelType);
    if (key === "details") return Boolean(name.trim());
    return true; // "tune" is always valid (has defaults)
  }

  return (
    <section>
      {/* Sub-tab switcher — top-left and sticky, so it stays in reach while
          scrolling. The negative margins + padding let the backdrop span the
          full content width so scrolled content is covered cleanly. */}
      <div className="sticky top-0 z-20 -mx-6 mb-6 border-b border-slate-800 bg-slate-950/90 px-6 py-3 backdrop-blur">
        <div className="inline-flex rounded-lg border border-slate-700 bg-slate-800 p-1">
          {[
            ["train", "Train"],
            ["models", "Models"],
          ].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setView(key)}
              className={`flex items-center gap-2 rounded-md px-4 py-1.5 text-sm font-medium transition ${
                view === key
                  ? "bg-emerald-500 text-white"
                  : "text-slate-400 hover:text-slate-100"
              }`}
            >
              {label}
              {key === "models" && jobs.length > 0 && (
                <span
                  className={`rounded-full px-1.5 text-xs ${
                    view === key
                      ? "bg-emerald-600 text-white"
                      : "bg-slate-700 text-slate-300"
                  }`}
                >
                  {jobs.length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      {view === "train" ? (
        /* ---------------- Train: vertical form ---------------- */
        <div className="mx-auto max-w-xl">
          {/* Stepper */}
          <ol className="mb-5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
            {stepDefs.map((s, i) => (
              <li key={s.key} className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={i > step}
                  onClick={() => i <= step && setStep(i)}
                  className={`flex items-center gap-1.5 font-medium transition ${
                    i === step
                      ? "text-emerald-300"
                      : i < step
                        ? "text-slate-300 hover:text-white"
                        : "text-slate-600"
                  }`}
                >
                  <span
                    className={`flex h-5 w-5 items-center justify-center rounded-full border text-[10px] ${
                      i === step
                        ? "border-emerald-400 bg-emerald-500/20 text-emerald-200"
                        : i < step
                          ? "border-emerald-500 bg-emerald-500 text-white"
                          : "border-slate-600"
                    }`}
                  >
                    {i < step ? "✓" : i + 1}
                  </span>
                  {s.label}
                </button>
                {i < stepDefs.length - 1 && (
                  <span className="text-slate-600">→</span>
                )}
              </li>
            ))}
          </ol>

          {/* Current step */}
          <div className="rounded-xl border border-slate-700 bg-slate-800 p-6">
            <h3 className="text-base font-semibold">{current.label}</h3>
            <p className="mb-4 mt-0.5 text-xs text-slate-400">{current.hint}</p>

            {current.key === "dataset" && (
              <select
                value={datasetId}
                onChange={(e) => setDatasetId(e.target.value)}
                className={inputClass}
              >
                <option value="">Select a dataset…</option>
                {datasets
                  .filter((d) => d.status === "ready")
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name || d.filename} ({d.modality})
                    </option>
                  ))}
              </select>
            )}

            {current.key === "target" && (
              <div className="space-y-4">
                <div>
                  <label className={labelClass}>Target column</label>
                  <Combobox
                    options={columns}
                    value={targetColumn}
                    onChange={setTargetColumn}
                    placeholder={
                      datasetId ? "Search columns…" : "Pick a dataset first"
                    }
                  />
                </div>
                <div>
                  <label className={labelClass}>Task</label>
                  <select
                    value={taskType}
                    onChange={(e) => setTaskType(e.target.value)}
                    className={inputClass}
                  >
                    <option value="classification">classification</option>
                    <option value="regression">regression</option>
                  </select>
                </div>
              </div>
            )}

            {current.key === "model" && (
              <div>
                {models.length > 4 && (
                  <div className="relative mb-3">
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
                      value={modelQuery}
                      onChange={(e) => setModelQuery(e.target.value)}
                      placeholder="Search models…"
                      className="w-full rounded-lg border border-slate-600 bg-slate-700 py-2 pl-9 pr-3 text-sm text-slate-100 transition focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
                    />
                  </div>
                )}
                <div className="grid grid-cols-2 gap-3">
                  {filteredModels.map((m) => {
                    const meta = MODEL_META[m.name] || {
                      label: m.name,
                      family: "",
                      desc: "",
                    };
                    const selected = modelType === m.name;
                    return (
                      <button
                        type="button"
                        key={m.name}
                        onClick={() => setModelType(m.name)}
                        className={`rounded-lg border p-3 text-left transition ${
                          selected
                            ? "border-emerald-500 bg-emerald-500/10 ring-1 ring-emerald-500"
                            : "border-slate-700 bg-slate-900/40 hover:border-slate-600"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-sm font-medium text-slate-100">
                            {meta.label}
                          </span>
                          {selected && (
                            <span className="text-sm text-emerald-400">✓</span>
                          )}
                        </div>
                        <p className="mt-1 text-xs text-slate-400">{meta.desc}</p>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {meta.family && (
                            <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-400">
                              {meta.family}
                            </span>
                          )}
                          {meta.recommended && (
                            <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-emerald-300">
                              Recommended
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
                {filteredModels.length === 0 && (
                  <p className="text-xs text-slate-400">
                    No models match “{modelQuery}”.
                  </p>
                )}
              </div>
            )}

            {current.key === "tune" && (
              <div className="space-y-4">
                {currentParams.length > 0 ? (
                  <div className="grid grid-cols-2 gap-4">
                    {currentParams.map((p) => (
                      <div key={p.name}>
                        <label className="mb-1 block text-xs text-slate-400">
                          {p.label}
                        </label>
                        {p.type === "select" ? (
                          <select
                            value={hyperparams[p.name] ?? p.default}
                            onChange={(e) => setParam(p.name, e.target.value)}
                            className={inputClass}
                          >
                            {p.options.map((o) => (
                              <option key={o} value={o}>
                                {o}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type="number"
                            step={p.type === "float" ? "0.01" : "1"}
                            value={hyperparams[p.name] ?? p.default}
                            onChange={(e) => setParam(p.name, e.target.value)}
                            className={inputClass}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">
                    This model has no tunable hyperparameters.
                  </p>
                )}

                {!isImage && (
                  <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-700 bg-slate-900/50 p-3">
                    <input
                      type="checkbox"
                      checked={scaleFeatures}
                      onChange={(e) => setScaleFeatures(e.target.checked)}
                      className="mt-0.5 h-4 w-4"
                    />
                    <span>
                      <span className="text-sm font-medium text-slate-200">
                        Scale features
                      </span>
                      <span className="block text-xs text-slate-400">
                        Standardize inputs before training — helps SVM, KNN, MLP
                        &amp; linear models.
                      </span>
                    </span>
                  </label>
                )}
              </div>
            )}

            {current.key === "details" && (
              <div className="space-y-4">
                <div>
                  <label className={labelClass}>Model name</label>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. student-pass-predictor"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Description (optional)</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                    placeholder="Notes about this run…"
                    className={inputClass}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Wizard navigation */}
          <div className="mt-4 flex items-center justify-between">
            <button
              type="button"
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0}
              className="rounded-lg px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:text-white disabled:opacity-40"
            >
              Back
            </button>
            {isLastStep ? (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!stepValid("details")}
                className={btnPrimary}
              >
                Train model
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setStep((s) => s + 1)}
                disabled={!stepValid(current.key)}
                className={btnPrimary}
              >
                Next
              </button>
            )}
          </div>
        </div>
      ) : (
        /* ---------------- Models: trained jobs table ---------------- */
        <div className="overflow-hidden rounded-xl border border-slate-700">
          <table className="w-full bg-slate-800 text-sm">
            <thead className="bg-slate-700/50 text-left text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Model</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Target</th>
                <th className="px-4 py-3 font-medium">Metrics</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-4 py-10 text-center text-slate-400">
                    No models trained yet. Switch to{" "}
                    <button
                      onClick={() => setView("train")}
                      className="font-medium text-emerald-400 hover:underline"
                    >
                      Train
                    </button>{" "}
                    to create one.
                  </td>
                </tr>
              ) : (
                jobs.map((j) => (
                  <tr
                    key={j.id}
                    className="border-t border-slate-700 transition hover:bg-slate-700/30"
                  >
                    <td className="px-4 py-3 text-slate-400">{j.id}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium">{j.name || "—"}</div>
                      {j.description && (
                        <div className="max-w-[16rem] truncate text-xs text-slate-500">
                          {j.description}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-300">
                      {j.model_type}
                      {j.scale_features ? " (scaled)" : ""}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          STATUS_COLORS[j.status] || ""
                        }`}
                      >
                        {j.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{j.target_column}</td>
                    <td className="px-4 py-3 text-xs">
                      {j.status === "running" && j.progress ? (
                        <TrainingProgress progress={j.progress} />
                      ) : j.metrics ? (
                        <span className="font-mono text-slate-300">
                          {Object.entries(j.metrics)
                            .map(([k, v]) => `${k}=${Number(v).toFixed(3)}`)
                            .join("  ")}
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDelete(j.id)}
                        className="rounded-md border border-red-500/40 px-2.5 py-1 text-xs font-medium text-red-400 transition hover:bg-red-500/10"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// A tiny inline-SVG line chart (no library) — plots values left→right, scaled to
// fit, with a dot on the latest point. Used for the per-epoch accuracy curve.
function Sparkline({ values, width = 64, height = 18 }) {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const x = (i) => (i / (values.length - 1)) * width;
  const y = (v) => height - ((v - min) / range) * height;
  const points = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <svg width={width} height={height} className="shrink-0">
      <polyline points={points} fill="none" stroke="#34d399" strokeWidth="1.5" />
      <circle cx={width} cy={y(values[values.length - 1])} r="2" fill="#34d399" />
    </svg>
  );
}

// Live training progress for a running epoch-based job: epoch X/Y, a progress
// bar, the accuracy sparkline, and the latest val-accuracy.
function TrainingProgress({ progress }) {
  const { current_epoch, total_epochs, history = [] } = progress;
  const accuracies = history.map((h) => h.val_accuracy).filter((v) => v != null);
  const latest = accuracies[accuracies.length - 1];
  const pct = total_epochs ? (current_epoch / total_epochs) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <span className="text-slate-400">
          Epoch {current_epoch}/{total_epochs}
        </span>
        <Sparkline values={accuracies} />
        {latest != null && (
          <span className="text-emerald-300">acc {latest.toFixed(2)}</span>
        )}
      </div>
      <div className="h-1 w-28 rounded bg-slate-700">
        <div className="h-1 rounded bg-emerald-500" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

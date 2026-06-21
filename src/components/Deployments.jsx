import { useEffect, useState } from "react";
import { listDeployments, createDeployment, predict } from "../api";

export default function Deployments() {
  const [deployments, setDeployments] = useState([]);
  const [error, setError] = useState("");
  // Create-deployment form
  const [modelVersion, setModelVersion] = useState("1");
  // Predict form
  const [selectedId, setSelectedId] = useState("");
  const [featuresJson, setFeaturesJson] = useState(
    '{\n  "hours_studied": 8,\n  "prev_score": 80,\n  "attendance": 95\n}'
  );
  const [prediction, setPrediction] = useState(null);

  async function refresh() {
    try {
      setDeployments(await listDeployments());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    try {
      await createDeployment({
        model_name: "modelforge-model",
        model_version: modelVersion,
      });
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handlePredict(e) {
    e.preventDefault();
    setError("");
    setPrediction(null);
    try {
      const features = JSON.parse(featuresJson);
      const res = await predict(Number(selectedId), features);
      setPrediction(res.prediction);
    } catch (err) {
      setError(err.message);
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
          <label className="block text-xs text-slate-500">
            Model version (modelforge-model)
          </label>
          <input
            value={modelVersion}
            onChange={(e) => setModelVersion(e.target.value)}
            required
            className="rounded border px-2 py-1 text-sm"
          />
        </div>
        <button
          type="submit"
          className="rounded bg-emerald-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-600"
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
          </tr>
        </thead>
        <tbody>
          {deployments.length === 0 ? (
            <tr>
              <td colSpan="3" className="p-4 text-center text-slate-400">
                No deployments yet.
              </td>
            </tr>
          ) : (
            deployments.map((d) => (
              <tr key={d.id} className="border-t">
                <td className="p-2">{d.id}</td>
                <td className="p-2">{d.model_name}</td>
                <td className="p-2">{d.model_version}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* Predict */}
      <form onSubmit={handlePredict} className="rounded border bg-white p-4">
        <h3 className="mb-3 font-medium">Get a prediction</h3>
        <div className="mb-3">
          <label className="block text-xs text-slate-500">Deployment</label>
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            required
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
        <label className="block text-xs text-slate-500">Features (JSON)</label>
        <textarea
          value={featuresJson}
          onChange={(e) => setFeaturesJson(e.target.value)}
          rows={5}
          className="mb-3 w-full rounded border p-2 font-mono text-xs"
        />
        <button
          type="submit"
          className="rounded bg-emerald-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-600"
        >
          Predict
        </button>

        {prediction !== null && (
          <div className="mt-4 rounded bg-emerald-50 p-3 text-sm">
            Prediction: <span className="font-bold">{String(prediction)}</span>
          </div>
        )}
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}
    </section>
  );
}

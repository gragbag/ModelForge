import { useEffect, useState } from "react";
import { listDatasets, uploadDataset } from "../api";

export default function Datasets() {
  const [datasets, setDatasets] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      setDatasets(await listDatasets());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      await uploadDataset(file);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      e.target.value = ""; // reset so the same file can be re-selected
    }
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Datasets</h2>
        <label className="cursor-pointer rounded bg-emerald-500 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-600">
          {busy ? "Uploading..." : "Upload CSV"}
          <input
            type="file"
            accept=".csv"
            onChange={handleUpload}
            className="hidden"
          />
        </label>
      </div>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      <table className="w-full overflow-hidden rounded border bg-white text-sm">
        <thead className="bg-slate-100 text-left text-slate-600">
          <tr>
            <th className="p-2">ID</th>
            <th className="p-2">Filename</th>
            <th className="p-2">Rows</th>
            <th className="p-2">Columns</th>
          </tr>
        </thead>
        <tbody>
          {datasets.length === 0 ? (
            <tr>
              <td colSpan="4" className="p-4 text-center text-slate-400">
                No datasets yet — upload a CSV to get started.
              </td>
            </tr>
          ) : (
            datasets.map((d) => (
              <tr key={d.id} className="border-t">
                <td className="p-2">{d.id}</td>
                <td className="p-2">{d.filename}</td>
                <td className="p-2">{d.row_count}</td>
                <td className="p-2">{d.column_count}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </section>
  );
}

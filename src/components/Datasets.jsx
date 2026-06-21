import { useEffect, useState } from "react";
import {
  listDatasets,
  uploadDataset,
  deleteDataset,
  getDatasetPreview,
} from "../api";

export default function Datasets() {
  const [datasets, setDatasets] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(null); // which dataset id is open
  const [previews, setPreviews] = useState({}); // id -> { columns, rows } (cache)

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

  async function handleDelete(id) {
    setError("");
    try {
      await deleteDataset(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  // Toggle a row open/closed; lazily fetch + cache its preview the first time.
  async function togglePreview(id) {
    if (expanded === id) {
      setExpanded(null);
      return;
    }
    setExpanded(id);
    if (!previews[id]) {
      try {
        const p = await getDatasetPreview(id);
        setPreviews((prev) => ({ ...prev, [id]: p }));
      } catch (err) {
        setError(err.message);
      }
    }
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Datasets</h2>
        <label className="cursor-pointer rounded bg-emerald-500 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-600">
          {busy ? "Uploading..." : "Upload CSV"}
          <input type="file" accept=".csv" onChange={handleUpload} className="hidden" />
        </label>
      </div>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      <table className="w-full overflow-hidden rounded border bg-white text-sm">
        <thead className="bg-slate-100 text-left text-slate-600">
          <tr>
            <th className="p-2 w-8"></th>
            <th className="p-2">ID</th>
            <th className="p-2">Filename</th>
            <th className="p-2">Rows</th>
            <th className="p-2">Columns</th>
            <th className="p-2"></th>
          </tr>
        </thead>
        <tbody>
          {datasets.length === 0 ? (
            <tr>
              <td colSpan="6" className="p-4 text-center text-slate-400">
                No datasets yet — upload a CSV to get started.
              </td>
            </tr>
          ) : (
            datasets.map((d) => (
              <DatasetRow
                key={d.id}
                dataset={d}
                isOpen={expanded === d.id}
                preview={previews[d.id]}
                onToggle={() => togglePreview(d.id)}
                onDelete={() => handleDelete(d.id)}
              />
            ))
          )}
        </tbody>
      </table>
    </section>
  );
}

function DatasetRow({ dataset: d, isOpen, preview, onToggle, onDelete }) {
  return (
    <>
      <tr className="border-t">
        <td className="p-2">
          <button
            onClick={onToggle}
            className="text-slate-400 hover:text-slate-700"
            aria-label="Toggle preview"
          >
            {isOpen ? "▾" : "▸"}
          </button>
        </td>
        <td className="p-2">{d.id}</td>
        <td className="p-2">{d.filename}</td>
        <td className="p-2">{d.row_count}</td>
        <td className="p-2">{d.column_count}</td>
        <td className="p-2 text-right">
          <button
            onClick={onDelete}
            className="rounded border border-red-300 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
          >
            Delete
          </button>
        </td>
      </tr>

      {isOpen && (
        <tr className="bg-slate-50">
          <td colSpan="6" className="p-3">
            {!preview ? (
              <p className="text-xs text-slate-400">Loading preview…</p>
            ) : (
              <div className="overflow-x-auto">
                <p className="mb-2 text-xs font-medium text-slate-500">
                  First {preview.rows.length} rows
                </p>
                <table className="text-xs">
                  <thead>
                    <tr className="text-left text-slate-500">
                      {preview.columns.map((c) => (
                        <th key={c} className="border-b px-2 py-1">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row, i) => (
                      <tr key={i}>
                        {preview.columns.map((c) => (
                          <td key={c} className="border-b px-2 py-1">
                            {String(row[c])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

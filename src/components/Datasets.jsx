import { useEffect, useState } from "react";
import {
  listDatasets,
  uploadDataset,
  deleteDataset,
  getDatasetPreview,
} from "../api";
import {
  btnDanger,
  btnPrimary,
  rowClass,
  tableClass,
  tableWrap,
  tdClass,
  theadClass,
  thClass,
} from "../ui";

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
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Datasets</h2>
        <label className={`cursor-pointer ${btnPrimary}`}>
          {busy ? "Uploading…" : "Upload CSV"}
          <input type="file" accept=".csv" onChange={handleUpload} className="hidden" />
        </label>
      </div>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      <div className={tableWrap}>
        <table className={tableClass}>
          <thead className={theadClass}>
            <tr>
              <th className={`${thClass} w-8`}></th>
              <th className={thClass}>ID</th>
              <th className={thClass}>Filename</th>
              <th className={thClass}>Rows</th>
              <th className={thClass}>Columns</th>
              <th className={thClass}></th>
            </tr>
          </thead>
          <tbody>
            {datasets.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-4 py-10 text-center text-slate-400">
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
      </div>
    </section>
  );
}

function DatasetRow({ dataset: d, isOpen, preview, onToggle, onDelete }) {
  return (
    <>
      <tr className={rowClass}>
        <td className={tdClass}>
          <button
            onClick={onToggle}
            className="text-slate-400 transition hover:text-slate-200"
            aria-label="Toggle preview"
          >
            {isOpen ? "▾" : "▸"}
          </button>
        </td>
        <td className={`${tdClass} text-slate-400`}>{d.id}</td>
        <td className={`${tdClass} font-medium`}>{d.filename}</td>
        <td className={`${tdClass} text-slate-300`}>{d.row_count}</td>
        <td className={`${tdClass} text-slate-300`}>{d.column_count}</td>
        <td className={`${tdClass} text-right`}>
          <button onClick={onDelete} className={btnDanger}>
            Delete
          </button>
        </td>
      </tr>

      {isOpen && (
        <tr className="bg-slate-950">
          <td colSpan="6" className="px-4 py-4">
            {!preview ? (
              <p className="text-xs text-slate-400">Loading preview…</p>
            ) : (
              <div className="overflow-x-auto">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
                  First {preview.rows.length} rows
                </p>
                <table className="text-xs">
                  <thead>
                    <tr className="text-left text-slate-400">
                      {preview.columns.map((c) => (
                        <th
                          key={c}
                          className="border-b border-slate-700 px-3 py-1.5 font-medium"
                        >
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row, i) => (
                      <tr key={i}>
                        {preview.columns.map((c) => (
                          <td
                            key={c}
                            className="border-b border-slate-800 px-3 py-1.5 text-slate-300"
                          >
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

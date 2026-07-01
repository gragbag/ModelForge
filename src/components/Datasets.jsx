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

const STATUS_COLORS = {
  validating: "bg-blue-500/20 text-blue-300",
  ready: "bg-emerald-500/20 text-emerald-300",
  failed: "bg-red-500/20 text-red-300",
};

export default function Datasets() {
  const [datasets, setDatasets] = useState([]);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(null); // which dataset id is open
  const [previews, setPreviews] = useState({}); // id -> preview (cache)
  const [showUpload, setShowUpload] = useState(false);

  async function refresh() {
    try {
      setDatasets(await listDatasets());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh();
    // Poll so an image dataset's status (validating → ready/failed) updates live.
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, []);

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
        <button className={btnPrimary} onClick={() => setShowUpload(true)}>
          Upload dataset
        </button>
      </div>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      <div className={tableWrap}>
        <table className={tableClass}>
          <thead className={theadClass}>
            <tr>
              <th className={`${thClass} w-8`}></th>
              <th className={thClass}>Name</th>
              <th className={thClass}>Type</th>
              <th className={thClass}>Details</th>
              <th className={thClass}>Status</th>
              <th className={thClass}></th>
            </tr>
          </thead>
          <tbody>
            {datasets.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-4 py-10 text-center text-slate-400">
                  No datasets yet — upload a CSV or image zip to get started.
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

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onUploaded={() => {
            setShowUpload(false);
            refresh();
          }}
        />
      )}
    </section>
  );
}

function UploadModal({ onClose, onUploaded }) {
  const [name, setName] = useState("");
  const [modality, setModality] = useState("tabular");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const isImage = modality === "image";
  const accept = isImage ? ".zip" : ".csv";

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!name.trim() || !file) return;
    setBusy(true);
    try {
      await uploadDataset(file, { name: name.trim(), modality, description });
      onUploaded();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <form
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
        className={`w-full max-w-md space-y-4 ${cardClass}`}
      >
        <h3 className="text-lg font-semibold">New dataset</h3>

        <div>
          <label className={labelClass}>Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="e.g. student-scores"
            className={inputClass}
          />
        </div>

        <div>
          <label className={labelClass}>Type</label>
          <div className="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-1">
            {["tabular", "image"].map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => {
                  setModality(m);
                  setFile(null); // accepted file type changed
                }}
                className={`rounded-md px-4 py-1.5 text-sm font-medium capitalize transition ${
                  modality === m
                    ? "bg-emerald-500 text-white"
                    : "text-slate-400 hover:text-slate-100"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className={labelClass}>Description (optional)</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="What's in this dataset?"
            className={inputClass}
          />
        </div>

        <div>
          <label className={labelClass}>
            {isImage ? "Image zip (folder-per-class)" : "CSV file"}
          </label>
          <label className="block cursor-pointer rounded-lg border border-dashed border-slate-600 px-4 py-5 text-center text-sm text-slate-400 transition hover:border-slate-500">
            {file ? (
              <span className="text-slate-200">{file.name}</span>
            ) : (
              `Choose a ${accept} file…`
            )}
            <input
              type="file"
              accept={accept}
              onChange={(e) => setFile(e.target.files[0] || null)}
              className="hidden"
            />
          </label>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:text-white"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy || !name.trim() || !file}
            className={btnPrimary}
          >
            {busy ? "Uploading…" : "Upload"}
          </button>
        </div>
      </form>
    </div>
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
        <td className={tdClass}>
          <div className="font-medium">{d.name || d.filename}</div>
          {d.name && (
            <div className="text-xs text-slate-500">{d.filename}</div>
          )}
        </td>
        <td className={tdClass}>
          <span className="rounded bg-slate-700 px-1.5 py-0.5 text-xs uppercase tracking-wide text-slate-300">
            {d.modality}
          </span>
        </td>
        <td className={`${tdClass} text-slate-300`}>
          {d.modality === "image"
            ? d.meta
              ? `${d.meta.num_images} imgs · ${d.meta.num_classes} classes`
              : "—"
            : d.row_count != null
              ? `${d.row_count} × ${d.column_count}`
              : "—"}
        </td>
        <td className={tdClass}>
          <span
            title={d.error || ""}
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              STATUS_COLORS[d.status] || ""
            }`}
          >
            {d.status}
          </span>
        </td>
        <td className={`${tdClass} text-right`}>
          <button onClick={onDelete} className={btnDanger}>
            Delete
          </button>
        </td>
      </tr>

      {isOpen && (
        <tr className="bg-slate-950">
          <td colSpan="6" className="px-4 py-4">
            {d.description && (
              <p className="mb-3 text-xs italic text-slate-400">{d.description}</p>
            )}
            {!preview ? (
              <p className="text-xs text-slate-400">Loading preview…</p>
            ) : d.modality === "image" ? (
              <div className="text-xs text-slate-300">
                <p className="mb-2 font-medium uppercase tracking-wide text-slate-400">
                  {preview.num_images} images · {preview.num_classes} classes
                </p>
                <div className="flex flex-wrap gap-1">
                  {(preview.classes || []).map((c) => (
                    <span key={c} className="rounded bg-slate-700 px-2 py-0.5">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
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

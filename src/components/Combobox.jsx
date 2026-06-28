import { useEffect, useRef, useState } from "react";

// A small searchable dropdown: shows the selected value when closed; on focus it
// opens a filterable list of `options`. Click an option to select it.
export default function Combobox({ options, value, onChange, placeholder }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  // Close the dropdown when clicking outside it.
  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const filtered = options.filter((o) =>
    o.toLowerCase().includes(query.toLowerCase())
  );

  function select(option) {
    onChange(option);
    setQuery("");
    setOpen(false);
  }

  return (
    <div ref={ref} className="relative">
      <input
        // Show the live search query while open; the selected value while closed.
        value={open ? query : value}
        onFocus={() => {
          setQuery("");
          setOpen(true);
        }}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        placeholder={placeholder}
        className="w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-slate-100 transition focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
      />
      {open && (
        <ul className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-slate-600 bg-slate-800 text-sm shadow-lg">
          {filtered.length === 0 ? (
            <li className="px-3 py-2 text-slate-400">No matches</li>
          ) : (
            filtered.map((o) => (
              <li key={o}>
                <button
                  type="button"
                  onClick={() => select(o)}
                  className={`block w-full px-3 py-2 text-left transition hover:bg-slate-700 ${
                    o === value ? "bg-emerald-500/20 font-medium text-emerald-300" : ""
                  }`}
                >
                  {o}
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}

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
        className="w-44 rounded border px-2 py-1 text-sm focus:border-emerald-500 focus:outline-none"
      />
      {open && (
        <ul className="absolute z-10 mt-1 max-h-48 w-44 overflow-auto rounded border bg-white text-sm shadow">
          {filtered.length === 0 ? (
            <li className="px-2 py-1 text-slate-400">No matches</li>
          ) : (
            filtered.map((o) => (
              <li key={o}>
                <button
                  type="button"
                  onClick={() => select(o)}
                  className={`block w-full px-2 py-1 text-left hover:bg-emerald-50 ${
                    o === value ? "bg-emerald-100 font-medium" : ""
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

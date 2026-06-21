import { useState } from "react";
import { login, register, setToken } from "../api";

export default function Login({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (isRegister) {
        await register(email, password);
      }
      const { access_token } = await login(email, password);
      setToken(access_token);
      onLogin();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-900">
      <form
        onSubmit={handleSubmit}
        className="w-80 rounded-lg bg-white p-8 shadow-lg"
      >
        <h1 className="mb-1 text-center text-2xl font-bold text-slate-800">
          Model<span className="text-emerald-500">Forge</span>
        </h1>
        <p className="mb-6 text-center text-sm text-slate-500">
          {isRegister ? "Create an account" : "Sign in to continue"}
        </p>

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="mb-3 w-full rounded border px-3 py-2 text-sm"
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="mb-4 w-full rounded border px-3 py-2 text-sm"
        />

        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded bg-emerald-500 py-2 font-medium text-white hover:bg-emerald-600 disabled:opacity-50"
        >
          {busy ? "..." : isRegister ? "Register" : "Log in"}
        </button>

        <button
          type="button"
          onClick={() => setIsRegister((v) => !v)}
          className="mt-4 w-full text-center text-sm text-slate-500 hover:text-slate-800"
        >
          {isRegister
            ? "Already have an account? Log in"
            : "No account? Register"}
        </button>
      </form>
    </div>
  );
}

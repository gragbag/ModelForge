import { useState } from "react";
import { login, register, setToken } from "../api";
import { btnPrimary, inputClass, labelClass } from "../ui";

// `mode` is "login" or "register" (controlled by the navbar in PublicApp).
// `onSwitchMode` flips between the two; `onLogin` is called once authenticated.
export default function Login({ mode, onLogin, onSwitchMode }) {
  const isRegister = mode === "register";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    // Client-side checks for registration before hitting the API.
    if (isRegister) {
      if (password !== confirmPassword) {
        setError("Passwords do not match");
        return;
      }
      if (password.length < 8) {
        setError("Password must be at least 8 characters");
        return;
      }
    }

    setBusy(true);
    try {
      if (isRegister) await register(email, password);
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
    <div className="flex items-center justify-center px-4 py-16">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-xl border border-slate-700 bg-slate-800 p-8 shadow-lg"
      >
        <h2 className="mb-1 text-2xl font-bold text-slate-100">
          {isRegister ? "Create your account" : "Welcome back"}
        </h2>
        <p className="mb-6 text-sm text-slate-400">
          {isRegister
            ? "Sign up to start training models."
            : "Log in to your dashboard."}
        </p>

        <div className="mb-4">
          <label className={labelClass}>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className={inputClass}
          />
        </div>

        <div className="mb-4">
          <label className={labelClass}>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className={inputClass}
          />
        </div>

        {isRegister && (
          <div className="mb-4">
            <label className={labelClass}>Confirm password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className={inputClass}
            />
          </div>
        )}

        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

        <button type="submit" disabled={busy} className={`w-full ${btnPrimary}`}>
          {busy ? "…" : isRegister ? "Sign up" : "Log in"}
        </button>

        <button
          type="button"
          onClick={() => onSwitchMode(isRegister ? "login" : "register")}
          className="mt-4 w-full text-center text-sm text-slate-400 transition hover:text-slate-100"
        >
          {isRegister
            ? "Already have an account? Log in"
            : "Need an account? Sign up"}
        </button>
      </form>
    </div>
  );
}

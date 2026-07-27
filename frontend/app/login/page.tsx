"use client";

import { FormEvent, useState } from "react";
import { LogIn } from "lucide-react";

import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { error, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await login(email, password);
    } catch {
      setSaving(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <div>
          <p className="login-eyebrow">Beta privada</p>
          <h1>Eter ERP</h1>
          <p>Ingresa con tu usuario para acceder al centro de operaciones.</p>
        </div>
        <form className="form" onSubmit={submit}>
          {error ? <div className="notice notice-error">{error}</div> : null}
          <label className="field">
            <span>Email</span>
            <input
              autoComplete="email"
              inputMode="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Contrasena</span>
            <input
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <button className="button touch-button" type="submit" disabled={saving}>
            <LogIn size={18} /> {saving ? "Ingresando..." : "Ingresar"}
          </button>
        </form>
      </section>
    </main>
  );
}

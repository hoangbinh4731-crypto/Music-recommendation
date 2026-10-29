import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";

export default function Login({ onLogin }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  console.log("[DEBUG] Login rendered, onLogin =", typeof onLogin);

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    console.log("[DEBUG] submit clicked");
    try {
      const result = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      console.log("[DEBUG] login ok, response =", result, "| onLogin =", typeof onLogin);
      if (typeof onLogin === "function") {
        onLogin();
      } else {
        console.error("[DEBUG] onLogin is missing!");
      }
      navigate("/", { replace: true });
    } catch (err) {
      console.error("[DEBUG] login error:", err);
      setError(err.message);
    }
  }

  return (
    <form onSubmit={onSubmit}>
      <h1>Log in</h1>
      <label>
        Username
        <input value={username} onChange={(event) => setUsername(event.target.value)} />
      </label>
      <label>
        Password
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>
      {error ? <p className="error">{error}</p> : null}
      <button type="submit">Log in</button>
      <p>
        <Link to="/register">Create an account</Link>
      </p>
    </form>
  );
}
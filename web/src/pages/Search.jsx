import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Search() {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      const found = await api(`/tracks/search?q=${encodeURIComponent(query)}`);
      setRows(found);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h1>Search</h1>
      <form onSubmit={onSubmit}>
        <label>
          Title or artist
          <input value={query} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <button type="submit">Search</button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      <ul className="tracks">
        {rows.map((row) => (
          <li key={row.track_id}>
            <Link to={`/track/${row.track_id}`}>
              {row.title} — {row.artist_name}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

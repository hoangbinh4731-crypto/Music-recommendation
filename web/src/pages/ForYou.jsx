import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function ForYou() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/recommend/history")
      .then(setRows)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <section>
      <h1>For you</h1>
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

import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { API_BASE, api } from "../api";

const plays = new Map();

function postPlay(id) {
  const current = plays.get(id);
  if (current) {
    return current;
  }
  const request = api(`/play/${id}`, { method: "POST" }).finally(() => {
    if (plays.get(id) === request) {
      plays.delete(id);
    }
  });
  plays.set(id, request);
  return request;
}

export default function Track() {
  const { id } = useParams();
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setPayload(null);
    setError("");
    postPlay(id)
      .then((body) => {
        if (!cancelled) setPayload(body);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <section>
      <h1>{payload ? payload.track.title : `Track ${id}`}</h1>
      {payload ? <p>{payload.track.artist_name}</p> : null}
      <audio controls src={`${API_BASE}/audio/${id}`} />
      {error ? <p className="error">{error}</p> : null}
      <h2>Similar</h2>
      <ul className="tracks">
        {(payload?.neighbors || []).map((row) => (
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

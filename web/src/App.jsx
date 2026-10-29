import { useEffect, useState } from "react";
import { Link, Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { api } from "./api";
import ForYou from "./pages/ForYou";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Search from "./pages/Search";
import Track from "./pages/Track";

const FLAG = "musicrec_logged_in";

function Landing() {
  console.log("[DEBUG] Landing rendered");
  return (
    <section className="hero">
      <h2 className="hero-text">
        Hòa mình vào âm nhạc,<br />
        khám phá thế giới của<br />
        riêng bạn.
      </h2>
      <div className="hero-actions">
        <Link to="/login" className="btn">Log in</Link>
        <Link to="/register" className="btn ghost">Register</Link>
      </div>
    </section>
  );
}

function Private({ loggedIn, children }) {
  return loggedIn ? children : <Navigate to="/" replace />;
}

export default function App() {
  const navigate = useNavigate();
  const [loggedIn, setLoggedIn] = useState(() => localStorage.getItem(FLAG) === "1");

  // Log mỗi khi loggedIn thay đổi
  useEffect(() => {
    console.log("[DEBUG] loggedIn =", loggedIn, "| localStorage =", localStorage.getItem(FLAG));
  }, [loggedIn]);

  function handleLogin() {
    console.log("[DEBUG] handleLogin called");
    localStorage.setItem(FLAG, "1");
    setLoggedIn(true);
  }

  async function handleLogout() {
    console.log("[DEBUG] handleLogout called");
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      /* the API may not have a logout route; the page still logs out */
    }
    localStorage.removeItem(FLAG);
    setLoggedIn(false);
    navigate("/");
  }

  return (
    <div className="sheet">
      <header className="top">
        <Link to="/" className="brand">Music recommendation system</Link>
        {loggedIn ? (
          <nav>
            <NavLink to="/" end>Search</NavLink>
            <NavLink to="/for-you">For you</NavLink>
            <button type="button" className="logout" onClick={handleLogout}>Log out</button>
          </nav>
        ) : null}
      </header>
      <main>
        <Routes>
          <Route path="/" element={loggedIn ? <Search /> : <Landing />} />
          <Route path="/login" element={<Login onLogin={handleLogin} />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/track/:id"
            element={<Private loggedIn={loggedIn}><Track /></Private>}
          />
          <Route
            path="/for-you"
            element={<Private loggedIn={loggedIn}><ForYou /></Private>}
          />
        </Routes>
      </main>
    </div>
  );
}
import { Link, Route, Routes } from "react-router-dom";
import ForYou from "./pages/ForYou";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Search from "./pages/Search";
import Track from "./pages/Track";

export default function App() {
  return (
    <div className="sheet">
      <nav>
        <Link to="/">Search</Link>
        <Link to="/for-you">For you</Link>
        <Link to="/login">Log in</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Search />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/track/:id" element={<Track />} />
        <Route path="/for-you" element={<ForYou />} />
      </Routes>
    </div>
  );
}

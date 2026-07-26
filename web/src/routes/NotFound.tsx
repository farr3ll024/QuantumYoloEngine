import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="page">
      <h1>Page not found</h1>
      <p>
        <Link to="/">Return home</Link>
      </p>
    </div>
  );
}

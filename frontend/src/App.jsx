import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import { useAuth } from "./context/AuthContext.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Tasks from "./pages/Tasks.jsx";
import VirtualMachines from "./pages/VirtualMachines.jsx";
import Analytics from "./pages/Analytics";
import Reporting from "./pages/Reporting.jsx";
import Replay from "./pages/Replay.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";

function RequireAuth({ children }) {
  const { user, accessToken } = useAuth();

  if (!user || !accessToken) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function HomeRedirect() {
  const { user, accessToken } = useAuth();

  return (
    <Navigate
      to={user && accessToken ? "/dashboard" : "/login"}
      replace
    />
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
        <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
        <Route path="/reports" element={<ProtectedRoute><Reporting /></ProtectedRoute>} />
        <Route path="/replay" element={<ProtectedRoute><Replay /></ProtectedRoute>} />
        <Route
          path="/tasks"
          element={
            <RequireAuth>
              <Tasks />
            </RequireAuth>
          }
        />

        <Route
          path="/vms"
          element={
            <RequireAuth>
              <VirtualMachines />
            </RequireAuth>
          }
        />

        <Route path="*" element={<HomeRedirect />} />
      </Routes>
    </BrowserRouter>
  );
}
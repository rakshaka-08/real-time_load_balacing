import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import { useAuth } from "./context/AuthContext.jsx";

import ProtectedRoute from "./components/ProtectedRoute.jsx";

import Analytics from "./pages/Analytics.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Login from "./pages/Login.jsx";
import NotFound from "./pages/NotFound.jsx";
import Register from "./pages/Register.jsx";
import Replay from "./pages/Replay.jsx";
import Reporting from "./pages/Reporting.jsx";
import SystemStatus from "./pages/SystemStatus.jsx";
import Tasks from "./pages/Tasks.jsx";
import VirtualMachines from "./pages/VirtualMachines.jsx";

function HomeRedirect() {
  const { user, accessToken } = useAuth();

  return (
    <Navigate
      to={user && accessToken ? "/dashboard" : "/login"}
      replace
    />
  );
}

function ProtectedPage({ children }) {
  return <ProtectedRoute>{children}</ProtectedRoute>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomeRedirect />} />

        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        <Route
          path="/dashboard"
          element={
            <ProtectedPage>
              <Dashboard />
            </ProtectedPage>
          }
        />

        <Route
          path="/tasks"
          element={
            <ProtectedPage>
              <Tasks />
            </ProtectedPage>
          }
        />

        <Route
          path="/vms"
          element={
            <ProtectedPage>
              <VirtualMachines />
            </ProtectedPage>
          }
        />

        <Route
          path="/analytics"
          element={
            <ProtectedPage>
              <Analytics />
            </ProtectedPage>
          }
        />

        <Route
          path="/reports"
          element={
            <ProtectedPage>
              <Reporting />
            </ProtectedPage>
          }
        />

        <Route
          path="/replay"
          element={
            <ProtectedPage>
              <Replay />
            </ProtectedPage>
          }
        />

        <Route
          path="/status"
          element={
            <ProtectedPage>
              <SystemStatus />
            </ProtectedPage>
          }
        />

        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}
import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { AppProvider } from "./context/AppContext";
import { ChatProvider } from "./context/ChatContext";
import { ProtectedRoute, GuestRoute } from "./components/auth/ProtectedRoute";
import { PageSpinner } from "./components/common/Spinner";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Privacy } from "./pages/Privacy";
import { Safety } from "./pages/Safety";
import { NotFound } from "./pages/NotFound";

const Chat = lazy(() => import("./pages/Chat").then((mod) => ({ default: mod.Chat })));
const ChatHistory = lazy(() => import("./pages/ChatHistory").then((mod) => ({ default: mod.ChatHistory })));
const Profile = lazy(() => import("./pages/Profile").then((mod) => ({ default: mod.Profile })));
const Dashboard = lazy(() => import("./pages/Dashboard").then((mod) => ({ default: mod.Dashboard })));
const Evaluation = lazy(() => import("./pages/Evaluation").then((mod) => ({ default: mod.Evaluation })));

function ProtectedPage({ children, label }: { children: ReactNode; label: string }) {
  return (
    <ProtectedRoute>
      <Suspense fallback={<PageSpinner label={label} />}>{children}</Suspense>
    </ProtectedRoute>
  );
}

function ProtectedChatLayout() {
  return (
    <ProtectedRoute>
      <ChatProvider>
        <Suspense fallback={<PageSpinner label="Loading..." />}>
          <Outlet />
        </Suspense>
      </ChatProvider>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route
            path="/login"
            element={
              <GuestRoute>
                <Login />
              </GuestRoute>
            }
          />
          <Route
            path="/register"
            element={
              <GuestRoute>
                <Register />
              </GuestRoute>
            }
          />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/safety" element={<Safety />} />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Suspense fallback={<PageSpinner label="Loading profile..." />}>
                  <Profile />
                </Suspense>
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedPage label="Loading dashboard...">
                <Dashboard />
              </ProtectedPage>
            }
          />
          <Route
            path="/evaluation"
            element={
              <ProtectedPage label="Loading evaluation...">
                <Evaluation />
              </ProtectedPage>
            }
          />
          <Route element={<ProtectedChatLayout />}>
            <Route path="/chat" element={<Chat />} />
            <Route path="/chat/:chatId" element={<Chat />} />
            <Route path="/history" element={<ChatHistory />} />
          </Route>
          <Route path="/app" element={<Navigate to="/chat" replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AppProvider>
    </AuthProvider>
  );
}

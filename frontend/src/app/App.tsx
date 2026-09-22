import { lazy, Suspense } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router";
import { RequireAuth } from "../auth/AuthProvider";
import { Layout } from "../components/Layout";
import { ConnectorsPage } from "../pages/ConnectorsPage";
import { InvestigationsPage } from "../pages/InvestigationsPage";
import { LoginPage } from "../pages/LoginPage";
import { ReportPage } from "../pages/ReportPage";
import { WarRoomPage } from "../pages/WarRoomPage";

const queryClient = new QueryClient();

// Development-only office preview; the import is dropped from production builds.
const OfficePreview = import.meta.env.DEV
  ? lazy(() => import("../dev/OfficePreview").then((m) => ({ default: m.OfficePreview })))
  : null;

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          {OfficePreview && (
            <Route path="/dev/office" element={<Suspense fallback={null}><OfficePreview /></Suspense>} />
          )}
          <Route element={<RequireAuth><Layout /></RequireAuth>}>
            <Route index element={<WarRoomPage />} />
            <Route path="connectors" element={<ConnectorsPage />} />
            <Route path="investigations" element={<InvestigationsPage />} />
            <Route path="investigations/:id" element={<WarRoomPage />} />
            <Route path="investigations/:id/report" element={<ReportPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router";
import { RequireAuth } from "../auth/AuthProvider";
import { Layout } from "../components/Layout";
import { InvestigationPage } from "../pages/InvestigationPage";
import { InvestigationsPage } from "../pages/InvestigationsPage";
import { LoginPage } from "../pages/LoginPage";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth><Layout /></RequireAuth>}>
            <Route index element={<InvestigationsPage />} />
            <Route path="investigations/:id" element={<InvestigationPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

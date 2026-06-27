import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { getErrorMessage } from "./api/client";
import { AuthProvider } from "./auth/AuthProvider";
import ProtectedRoute from "./auth/ProtectedRoute";
import AppLayout from "./components/layout/AppLayout";
import ExplorerPage from "./pages/ExplorerPage";
import ImageDetailPage from "./pages/ImageDetailPage";
import LoginPage from "./pages/LoginPage";
import StatsPage from "./pages/StatsPage";
import { toast } from "./toast/toastStore";
import Toaster from "./toast/Toaster";

// Surface every failed query/mutation as a toast, so errors pop up on any page.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
  queryCache: new QueryCache({
    onError: (error, query) => {
      // Queries can opt out of the global error toast (e.g. background lookups).
      if (query.meta?.suppressErrorToast) return;
      toast.error(getErrorMessage(error));
    },
  }),
  mutationCache: new MutationCache({
    onError: (error) => toast.error(getErrorMessage(error)),
  }),
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/" element={<ExplorerPage />} />
                <Route path="/stats" element={<StatsPage />} />
                <Route path="/image/:id" element={<ImageDetailPage />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
      <Toaster />
    </QueryClientProvider>
  );
}

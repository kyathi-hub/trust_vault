import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoadingScreen } from "@/components/ui/LoadingScreen";
import { Toaster } from "@/components/ui/Toaster";

// Pages
import { DashboardPage } from "@/pages/DashboardPage";
import { MyDocumentsPage } from "@/pages/MyDocumentsPage";
import { SharedWithMePage } from "@/pages/SharedWithMePage";
import { DocumentDetailPage } from "@/pages/DocumentDetailPage";
import { UploadDocumentPage } from "@/pages/UploadDocumentPage";
import { SearchPage } from "@/pages/SearchPage";
import { AdminUsersPage } from "@/pages/AdminUsersPage";
import { AdminAuditPage } from "@/pages/AdminAuditPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { AccessDeniedPage } from "@/pages/AccessDeniedPage";

function AppRoutes() {
  const { isLoading, isAuthenticated, user } = useAuth();

  if (isLoading) return <LoadingScreen />;
  if (!isAuthenticated) return <LoadingScreen message="Redirecting to login…" />;

  const isAdmin = user?.role === "admin";
  const isOwner = user?.role === "owner" || isAdmin;

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="/documents" element={<MyDocumentsPage />} />
          <Route path="/documents/upload" element={
            isOwner ? <UploadDocumentPage /> : <Navigate to="/access-denied" replace />
          } />
          <Route path="/documents/:id" element={<DocumentDetailPage />} />
          <Route path="/shared" element={<SharedWithMePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/profile" element={<ProfilePage />} />

          {/* Admin-only routes */}
          <Route path="/admin/users" element={
            isAdmin ? <AdminUsersPage /> : <Navigate to="/access-denied" replace />
          } />
          <Route path="/admin/audit" element={
            isAdmin ? <AdminAuditPage /> : <Navigate to="/access-denied" replace />
          } />

          <Route path="/access-denied" element={<AccessDeniedPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
      <Toaster />
    </AuthProvider>
  );
}

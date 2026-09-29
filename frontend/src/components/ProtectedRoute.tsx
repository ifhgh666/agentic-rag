import type { ReactNode } from "react";

export function ProtectedRoute({ authenticated, children }: { authenticated: boolean; children: ReactNode }) {
  if (!authenticated) return null;
  return <>{children}</>;
}

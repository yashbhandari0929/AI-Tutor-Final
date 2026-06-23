// LOCATION: app/(auth)/layout.tsx
// Auth pages handle their own full-screen dark background.
// No shell, no navbar, no sidebar.
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
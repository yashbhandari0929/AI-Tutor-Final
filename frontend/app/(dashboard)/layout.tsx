// LOCATION: app/(dashboard)/layout.tsx
// Replace your existing dashboard layout with this

import Navbar from "@/components/Navbar";
import Sidebar from "@/components/sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-[#060d1f] overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto bg-[#060d1f]">
          {children}
        </main>
      </div>
    </div>
  );
}
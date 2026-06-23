"use client";

import { usePathname } from "next/navigation";

const NO_SHELL_ROUTES = ["/login"];

export default function LayoutShell({
  children,
  sidebar,
  navbar,
}: {
  children: React.ReactNode;
  sidebar: React.ReactNode;
  navbar: React.ReactNode;
}) {
  const pathname = usePathname();
  const hideShell = NO_SHELL_ROUTES.includes(pathname);

  if (hideShell) {
    return <>{children}</>;
  }

  return (
    <div className="flex">
      {sidebar}
      <div className="flex-1">
        {navbar}
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
// components/Sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  BookOpen,
  BriefcaseBusiness,
  CalendarCheck,
  FileText,
  LayoutGrid,
  MessageSquare,
  PenLine,
  User,
} from "lucide-react";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutGrid },
  { label: "Chat", href: "/chat", icon: MessageSquare },
  { label: "Notes", href: "/notes", icon: FileText },
  { label: "Quiz", href: "/quiz", icon: PenLine },
  { label: "Study Plan", href: "/study-plan", icon: CalendarCheck },
  { label: "Resume Interview", href: "/resume-interview", icon: BriefcaseBusiness },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "Profile", href: "/profile", icon: User },
];

export default function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/dashboard"
      ? pathname === "/dashboard"
      : pathname === href || pathname.startsWith(href + "/");

  return (
    <aside className="flex h-full w-60 flex-col border-r border-white/5 bg-[#0a0e1a] px-3 py-5">
      <div className="mb-8 px-2 text-lg font-bold text-white">AI Tutor</div>

      <nav className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map(({ label, href, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
              isActive(href)
                ? "bg-indigo-500/15 text-indigo-300"
                : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
            }`}
          >
            <Icon size={17} strokeWidth={1.75} />
            <span className="truncate">{label}</span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}

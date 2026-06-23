// components/Sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutGrid,
  FileText,
  PenLine,
  BarChart3,
  MessageSquare,
  PlayCircle,
  Brain,
  User,
  BriefcaseBusiness,
} from "lucide-react";

// ── Adjust these hrefs to match your actual app/page.tsx file paths ──────────
// Your old sidebar used /notes, /quiz, /analytics etc. (not /dashboard/notes).
// The two columns below let you see both at a glance so you can sync them with
// your folder structure:
//
//   Old (working)            → kept here
//   /dashboard               → /dashboard        (same — root of the app)
//   /notes                   → /notes
//   /quiz                    → /quiz
//   /analytics               → /analytics
//   /chat                    → /chat             (was "AI Tutor")
//   (new) /video-tutor
//   (new) /flashcards
//   /profile                 → /profile
//
// If your pages live under /dashboard/* instead, swap the hrefs below.
// ─────────────────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { label: "Dashboard",   href: "/dashboard",    icon: LayoutGrid    },
  { label: "Notes",       href: "/notes",         icon: FileText      },
  { label: "Quiz",        href: "/quiz",          icon: PenLine       },
  { label: "Analytics",   href: "/analytics",     icon: BarChart3     },
  { label: "Chat",        href: "/chat",          icon: MessageSquare },
  { label: "Interview Prep", href: "/interview",  icon: BriefcaseBusiness },
  { label: "Video Tutor", href: "/video-tutor",   icon: PlayCircle    },
  { label: "Flashcards",  href: "/flashcards",    icon: Brain         },
  { label: "Profile",     href: "/profile",       icon: User          },
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
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}

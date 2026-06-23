"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { getSession } from "@/lib/auth";

// Pages an already-logged-in user shouldn't be able to sit on.
const AUTH_PAGES = ["/login", "/signup"];

export function useAuth() {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const session = getSession();
    const onAuthPage = AUTH_PAGES.includes(pathname);

    if (!session && !onAuthPage) {
      // Not logged in, trying to view a protected page → bounce to /login.
      router.replace("/login");
      return;
    }

    if (session && onAuthPage) {
      // Already logged in, sitting on /login or /signup → send to dashboard.
      router.replace("/dashboard");
    }
  }, [router, pathname]);
}
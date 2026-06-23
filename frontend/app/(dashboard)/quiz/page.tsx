// LOCATION: app/(dashboard)/quiz/page.tsx

"use client";

import { useAuth } from "@/hooks/useAuth";
import QuizCard from "@/components/QuizCard";

export default function QuizPage() {
  useAuth();

  return (
    <div className="min-h-screen bg-[#060d1f] px-8 py-8">
      <div className="pointer-events-none fixed -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-blue-600/10 blur-[120px]" />
      <div className="pointer-events-none fixed bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-indigo-700/10 blur-[90px]" />
      <div className="max-w-4xl mx-auto relative">
        <h1 className="text-4xl font-bold text-white mb-8">Quiz Generator</h1>
        <QuizCard />
      </div>
    </div>
  );
}
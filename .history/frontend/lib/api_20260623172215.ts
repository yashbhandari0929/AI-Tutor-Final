import { getToken } from "@/lib/auth";

const API_URL = "http://127.0.0.1:8000";

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = getToken();
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

const fetchWithTimeout = async (
  url: string,
  options: RequestInit = {},
  timeout = 60000
) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timer);
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || "Request failed");
    }
    return response;
  } catch (error) {
    clearTimeout(timer);
    throw error;
  }
};

/* ===========================
   NOTES API
=========================== */

export async function generateNotes(
  subject: string,
  topic: string,
  level: string,
  length: string,
  student_id: number | null = null
) {
  try {
    const response = await fetchWithTimeout(`${API_URL}/notes/generate`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ subject, topic, level, length, student_id }),
    });
    return await response.json();
  } catch (error) {
    console.error("Notes API Error:", error);
    return { notes: "Unable to generate notes right now. Please check backend logs." };
  }
}

/* ===========================
   QUIZ API
=========================== */

export async function generateQuiz(topic: string, difficulty: string, questions: number) {
  try {
    const response = await fetchWithTimeout(`${API_URL}/quiz/generate`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ topic, difficulty, questions }),
    });
    return await response.json();
  } catch (error) {
    console.error("Quiz API Error:", error);
    return {
      topic,
      difficulty,
      quiz: JSON.stringify([
        {
          question: "Quiz generation failed",
          options: ["Check Backend", "Check API Key", "Restart Server", "Try Again"],
          answer: "Try Again",
        },
      ]),
    };
  }
}

export async function saveQuizResult(
  topic: string,
  score: number,
  total_questions: number,
  student_id: number | null = null
) {
  const response = await fetch(`${API_URL}/quiz/result`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ topic, score, total_questions, student_id }),
  });
  return response.json();
}

/* ===========================
   ANALYTICS API
=========================== */

export async function getAnalyticsSummary() {
  const response = await fetchWithTimeout(`${API_URL}/analytics/summary`, {
    headers: authHeaders(),
  });
  return response.json();
}

/* ===========================
   PROFILE API
=========================== */

export async function getMyProfile() {
  const response = await fetchWithTimeout(`${API_URL}/profile/me`, {
    headers: authHeaders(),
  });
  return response.json();
}

export async function getProfileInfo() {
  const response = await fetchWithTimeout(`${API_URL}/students/profile-info`, {
    headers: authHeaders(),
  });
  return response.json();
}

/* ===========================
   VIDEOS API
=========================== */

export async function searchVideos(topic: string) {
  const response = await fetch(
    `${API_URL}/videos?topic=${encodeURIComponent(topic)}`,
    { headers: authHeaders() }
  );
  return response.json();
}

/* ===========================
   FLASHCARDS API
=========================== */

export interface FlashcardItem {
  question: string;
  answer: string;
}

export async function generateFlashcards(topic: string): Promise<FlashcardItem[]> {
  const response = await fetchWithTimeout(`${API_URL}/flashcards`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ topic }),
  });
  const data = await response.json();
  try {
    const cleaned = (data.flashcards as string).replace(/```json|```/g, "").trim();
    return JSON.parse(cleaned);
  } catch {
    console.error("Could not parse flashcards JSON:", data.flashcards);
    return [];
  }
}

/* ===========================
   DOCUMENTS (RAG) API
=========================== */

export interface UploadResponse {
  message: string;
  document_id: number;
  title: string;
  chunk_count: number;
  file_type?: "pdf" | "image";
}

export interface DocumentItem {
  id: number;
  title: string;
  source: string;
  uploaded_at: string;
  chunk_count: number;
  file_type: "pdf" | "image";
  conversation_id: number | null;
}

export interface DocumentListResponse {
  documents: DocumentItem[];
  total: number;
}

export interface DeleteResponse {
  message: string;
  document_id: number;
}

export async function uploadDocument(
  file: File,
  conversationId?: number
): Promise<UploadResponse> {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);
  if (conversationId !== undefined) {
    formData.append("conversation_id", String(conversationId));
  }
  const response = await fetchWithTimeout(
    `${API_URL}/documents/upload`,
    {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    },
    300_000
  );
  return response.json();
}

export async function listDocuments(conversationId?: number): Promise<DocumentListResponse> {
  const url =
    conversationId !== undefined
      ? `${API_URL}/documents?conversation_id=${conversationId}`
      : `${API_URL}/documents`;
  const response = await fetchWithTimeout(url, { headers: authHeaders() });
  return response.json();
}

export async function deleteDocument(documentId: number): Promise<DeleteResponse> {
  const response = await fetchWithTimeout(`${API_URL}/documents/${documentId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return response.json();
}

export async function getDocumentFileBlobUrl(documentId: number): Promise<string> {
  const response = await fetchWithTimeout(`${API_URL}/documents/${documentId}/file`, {
    headers: authHeaders(),
  });
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

/* ===========================
   CHAT API — legacy stateless
=========================== */

export interface ChatResponse {
  reply: string;
  used_rag?: boolean;
}

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const response = await fetchWithTimeout(`${API_URL}/chat`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ message }),
  });
  return response.json();
}

/* ===========================
   CONVERSATIONS API
=========================== */

export interface MessageItem {
  id: number;
  role: "user" | "assistant";
  content: string;
  used_rag: boolean;
  used_file_context?: boolean;
  sources?: string[];
  created_at: string;
}

export interface ConversationItem {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationAttachment {
  id: number;
  title: string;
  file_type: "pdf" | "image";
  chunk_count: number;
  uploaded_at: string;
}

export interface ConversationDetail extends ConversationItem {
  messages: MessageItem[];
  attachments: ConversationAttachment[];
}

export async function createConversation(): Promise<ConversationItem> {
  const response = await fetchWithTimeout(`${API_URL}/conversations`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
  });
  return response.json();
}

export async function listConversations(): Promise<{ conversations: ConversationItem[] }> {
  const response = await fetchWithTimeout(`${API_URL}/conversations`, {
    headers: authHeaders(),
  });
  return response.json();
}

export async function getConversation(conversationId: number): Promise<ConversationDetail> {
  const response = await fetchWithTimeout(`${API_URL}/conversations/${conversationId}`, {
    headers: authHeaders(),
  });
  return response.json();
}

export async function renameConversation(conversationId: number, title: string): Promise<ConversationItem> {
  const response = await fetchWithTimeout(`${API_URL}/conversations/${conversationId}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ title }),
  });
  return response.json();
}

export async function deleteConversation(conversationId: number): Promise<{ message: string }> {
  const response = await fetchWithTimeout(`${API_URL}/conversations/${conversationId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return response.json();
}

export interface SendMessageResponse {
  user_message: MessageItem;
  assistant_message: MessageItem;
  used_file_context?: boolean;
  sources?: string[];
}

export async function sendConversationMessage(
  conversationId: number,
  message: string
): Promise<SendMessageResponse> {
  const response = await fetchWithTimeout(
    `${API_URL}/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ message }),
    },
    120_000
  );
  return response.json();
}

/* ===========================
   DASHBOARD API
=========================== */

export interface TopicMasteryItem {
  topic: string;
  mastery_score: number;           // 0-100
  quiz_accuracy: number;
  consistency_score: number;
  completion_rate: number;
  time_score: number;
  attempts: number;
  last_seen: string | null;        // ISO date or null
  trend: "improving" | "declining" | "stable" | "new";
}

export interface DailyTask {
  order: number;
  task_type: "quiz" | "notes" | "review" | "flashcard" | "mock";
  topic: string;
  description: string;
  estimated_minutes: number;
  priority: "high" | "medium" | "low";
  difficulty: "easy" | "medium" | "hard" | "expert";
}

export interface WeeklyGoal {
  week_number: number;
  focus_area: string;
  target_accuracy: number;
  topics: string[];
  tasks_per_day: number;
  milestone: string;
}

export interface DashboardStudyPlan {
  // Legacy fields
  average_accuracy: number;
  plan: string[];

  // New structured fields
  accuracy_tier: "foundation" | "building" | "advancing" | "mastery";
  difficulty_level: "easy" | "medium" | "hard" | "expert";
  daily_plan: DailyTask[];
  weekly_plan: WeeklyGoal[];
  weak_topics: TopicMasteryItem[];
  strong_topics: TopicMasteryItem[];
  mastery_scores: TopicMasteryItem[];
  recommendations: string[];
  estimated_hours_to_next_tier: number;
  estimated_completion_date: string | null;
  current_streak: number;
  documents_available: number;
}

export interface FullStudyPlan extends DashboardStudyPlan {
  overall_accuracy: number;
  plan_generated_at: string;
}

export interface DashboardHeatmap {
  /** ISO date string (YYYY-MM-DD) → activity count */
  activity: Record<string, number>;
  /** Consecutive days of activity ending today, 0 if streak is broken */
  current_streak: number;
}

export async function getDashboardStudyPlan(): Promise<DashboardStudyPlan> {
  const response = await fetchWithTimeout(`${API_URL}/dashboard/study-plan`, {
    headers: authHeaders(),
  });
  return response.json();
}

export async function getDashboardHeatmap(): Promise<DashboardHeatmap> {
  const response = await fetchWithTimeout(`${API_URL}/dashboard/heatmap`, {
    headers: authHeaders(),
  });
  return response.json();
}

export async function getFullStudyPlan(): Promise<FullStudyPlan> {
  const response = await fetchWithTimeout(`${API_URL}/study-plan`, {
    headers: authHeaders(),
  });
  return response.json();
}

/* ===========================
   RECOMMENDATIONS API
=========================== */

export type RecommendationPriority = "high" | "medium" | "low";

export interface RecommendationTopic {
  topic: string;
  mastery: number;
  accuracy: number;
  attempts: number;
  correct_answers: number;
  notes_used: number;
  trend: "improving" | "declining" | "stable" | "new";
  consistency: number;
  score: number;
  last_practiced: string | null;
}

export interface RecommendationItem {
  type: string;
  title: string;
  description: string;
  priority: RecommendationPriority;
}

export interface RecommendationsResponse {
  learning_score: number;
  weak_topics: RecommendationTopic[];
  strong_topics: RecommendationTopic[];
  recommendations: RecommendationItem[];
}

export interface RecommendationSummary {
  weak_count: number;
  strong_count: number;
  recommendation_count: number;
}

export interface LearningPathItem {
  topic: string;
  current_level: "Beginner" | "Intermediate" | "Advanced";
  target_level: "Beginner" | "Intermediate" | "Advanced";
  estimated_days: number;
  tasks: string[];
}

export interface LearningPathResponse {
  overall_progress: number;
  estimated_completion_days: number;
  paths: LearningPathItem[];
}

export async function getRecommendations(): Promise<RecommendationsResponse> {
  const response = await fetchWithTimeout(`${API_URL}/recommendations`, {
    headers: authHeaders(),
  });
  return response.json();
}

export async function getRecommendationSummary(): Promise<RecommendationSummary> {
  const response = await fetchWithTimeout(`${API_URL}/recommendations/summary`, {
    headers: authHeaders(),
  });
  return response.json();
}

export async function getLearningPath(): Promise<LearningPathResponse> {
  const response = await fetchWithTimeout(`${API_URL}/learning-path`, {
    headers: authHeaders(),
  });
  return response.json();
}

/* ===========================
   INTERVIEW PREP API
=========================== */

export type InterviewDifficulty = "Easy" | "Medium" | "Hard";

export interface ResumeAnalysisResponse {
  session_id: number;
  resume_name: string;
  name: string;
  resume_score: number;
  ats_score: number;
  skills: string[];
  projects: string[];
  experience: string[];
  education: string[];
  skill_gap_analysis: string[];
  strengths: string[];
  improvements: string[];
}

export interface InterviewQuestionItem {
  id: number;
  question: string;
  category: "Technical" | "HR" | "Project-Based" | "Behavioral" | "Resume-Specific" | string;
  difficulty: string;
  answered?: boolean;
}

export interface InterviewEvaluationResponse {
  score: number;
  feedback: string;
  strengths: string[];
  weaknesses: string[];
  suggested_improvement: string;
  answer_id?: number;
}

export interface InterviewAnswerItem {
  id: number;
  question_id: number | null;
  answer: string;
  feedback: string;
  score: number;
}

export interface InterviewSessionItem {
  id: number;
  resume_name: string;
  resume_score: number;
  ats_score: number;
  created_at: string | null;
  question_count: number;
  answer_count: number;
  average_answer_score: number;
  questions: InterviewQuestionItem[];
  answers: InterviewAnswerItem[];
}

export interface InterviewHistoryResponse {
  sessions: InterviewSessionItem[];
}

export interface InterviewAnalyticsResponse {
  average_interview_score: number;
  best_interview_score: number;
  total_interviews: number;
  most_common_weak_areas: { area: string; count: number }[];
  skill_radar: { skill: string; score: number }[];
  question_categories_performance: { category: string; average_score: number; attempts: number }[];
}

export async function uploadResumeForInterview(file: File): Promise<ResumeAnalysisResponse> {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithTimeout(
    `${API_URL}/interview/upload`,
    {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    },
    180_000
  );
  return response.json();
}

export async function generateInterviewQuestions(
  sessionId: number,
  difficulty: InterviewDifficulty
): Promise<{ session_id: number; questions: InterviewQuestionItem[] }> {
  const response = await fetchWithTimeout(
    `${API_URL}/interview/generate`,
    {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ session_id: sessionId, difficulty }),
    },
    180_000
  );
  return response.json();
}

export async function evaluateInterviewAnswer(params: {
  question: string;
  answer: string;
  session_id?: number;
  question_id?: number;
}): Promise<InterviewEvaluationResponse> {
  const response = await fetchWithTimeout(
    `${API_URL}/interview/evaluate`,
    {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(params),
    },
    120_000
  );
  return response.json();
}

export async function getInterviewHistory(): Promise<InterviewHistoryResponse> {
  const response = await fetchWithTimeout(`${API_URL}/interview/history`, {
    headers: authHeaders(),
  });
  return response.json();
}

export async function getInterviewAnalytics(): Promise<InterviewAnalyticsResponse> {
  const response = await fetchWithTimeout(`${API_URL}/interview/analytics`, {
    headers: authHeaders(),
  });
  return response.json();
}
/* ===========================
   TOPIC MASTERY API
=========================== */

export type PersistedMasteryLevel =
  | "Mastered"
  | "Strong"
  | "Improving"
  | "Weak"
  | "Needs Work";

export interface StudentTopicMastery {
  id: number;
  student_id: number;
  topic: string;
  attempts: number;
  correct_answers: number;
  accuracy: number;
  mastery_level: PersistedMasteryLevel;
  last_practiced: string | null;
  created_at: string | null;
}

export interface MasterySummary {
  total_topics: number;
  total_attempts: number;
  total_correct_answers: number;
  average_accuracy: number;
  mastered_topics: number;
  strong_topics: number;
  improving_topics: number;
  weak_topics: number;
  needs_work_topics: number;
  mastery_distribution: Record<PersistedMasteryLevel, number>;
  last_practiced: string | null;
}

export async function getTopicMastery(): Promise<StudentTopicMastery[]> {
  const response = await fetchWithTimeout(`${API_URL}/mastery`, {
    headers: authHeaders(),
  });
  return response.json();
}

export async function getMasterySummary(): Promise<MasterySummary> {
  const response = await fetchWithTimeout(`${API_URL}/mastery/summary`, {
    headers: authHeaders(),
  });
  return response.json();
}

export async function getWeakTopics(): Promise<StudentTopicMastery[]> {
  const response = await fetchWithTimeout(`${API_URL}/mastery/weak-topics`, {
    headers: authHeaders(),
  });
  return response.json();
}

export async function getStrongTopics(): Promise<StudentTopicMastery[]> {
  const response = await fetchWithTimeout(`${API_URL}/mastery/strong-topics`, {
    headers: authHeaders(),
  });
  return response.json();
}

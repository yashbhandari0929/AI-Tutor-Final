"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import {
  ConversationItem,
  ConversationAttachment,
  MessageItem,
  createConversation,
  listConversations,
  getConversation,
  sendConversationMessage,
  deleteConversation,
  uploadDocument,
  getDocumentFileBlobUrl,
} from "@/lib/api";
import { Plus, Send, FileText, Image as ImageIcon, Trash2, MessageSquarePlus, Bot } from "lucide-react";

function decodeHtmlEntities(value: string) {
  return value
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, "\"")
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&");
}

function normalizeLegacyHtmlMessage(content: string) {
  if (!/<\/?[a-z][\s\S]*>/i.test(content) && !/&lt;\/?[a-z]/i.test(content)) {
    return content;
  }

  let text = decodeHtmlEntities(content);
  const replacements: Array<[RegExp, string]> = [
    [/<h1[^>]*>([\s\S]*?)<\/h1>/gi, "# $1\n\n"],
    [/<h2[^>]*>([\s\S]*?)<\/h2>/gi, "## $1\n\n"],
    [/<h3[^>]*>([\s\S]*?)<\/h3>/gi, "### $1\n\n"],
    [/<hr[^>]*\/?>/gi, "\n---\n"],
    [/<p[^>]*class=["']notes-numbered["'][^>]*>\s*(?:â€¢|•)?\s*([\s\S]*?)<\/p>/gi, "1. $1\n\n"],
    [/<li[^>]*>([\s\S]*?)<\/li>/gi, "- $1\n"],
    [/<p[^>]*>([\s\S]*?)<\/p>/gi, "$1\n\n"],
    [/<strong[^>]*>([\s\S]*?)<\/strong>/gi, "**$1**"],
    [/<em[^>]*>([\s\S]*?)<\/em>/gi, "*$1*"],
    [/<code[^>]*>([\s\S]*?)<\/code>/gi, "`$1`"],
  ];

  for (const [pattern, replacement] of replacements) {
    text = text.replace(pattern, replacement);
  }

  return decodeHtmlEntities(text)
    .replace(/<\/?(ul|ol)[^>]*>/gi, "\n")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function MarkdownMessage({ content }: { content: string }) {
  const normalizedContent = normalizeLegacyHtmlMessage(content);

  return (
    <div className="markdown-answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          h1: ({ children }) => (
            <h1 className="mb-3 text-2xl font-semibold leading-tight text-white">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="mb-2 mt-5 text-lg font-semibold leading-snug text-indigo-100">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="mb-2 mt-4 text-sm font-semibold uppercase tracking-wide text-indigo-200">
              {children}
            </h3>
          ),
          p: ({ children }) => <p className="my-2 leading-7 text-slate-200">{children}</p>,
          ul: ({ children }) => (
            <ul className="my-3 list-disc space-y-1.5 pl-5 marker:text-indigo-300">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="my-3 list-decimal space-y-1.5 pl-5 marker:font-semibold marker:text-indigo-300">
              {children}
            </ol>
          ),
          li: ({ children }) => <li className="pl-1 leading-7 text-slate-200">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="my-4 rounded-lg border border-indigo-300/20 bg-indigo-400/10 px-4 py-3 text-indigo-50">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto rounded-lg border border-white/10">
              <table className="w-full min-w-max border-collapse text-left text-xs">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-white/10 text-indigo-100">{children}</thead>,
          th: ({ children }) => (
            <th className="border-b border-white/10 px-3 py-2 font-semibold">{children}</th>
          ),
          td: ({ children }) => <td className="border-t border-white/10 px-3 py-2">{children}</td>,
          hr: () => <hr className="my-5 border-white/10" />,

          /*
  This is NOT a new file to use as-is — it's a reference snippet showing
  the exact patch to apply inside YOUR chat page component (the one with
  `MarkdownMessage`, `ReactMarkdown`, etc. — likely at app/chat/page.tsx
  or wherever your chat UI route lives, not app/page.tsx).

  Find this existing block inside the `components={{ ... }}` object passed
  to <ReactMarkdown>:

    code: ({ className, children, ...props }) => {
      const isInline = !className;
      return isInline ? (
        <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[0.85em] text-indigo-100" {...props}>
          {children}
        </code>
      ) : (
        <code className={`${className} font-mono text-xs`} {...props}>
          {children}
        </code>
      );
    },

  Replace it with:
*/

          code: ({ className, children, ...props }) => {
            const isInline = !className;
            const rawText = Array.isArray(children) ? children.join("") : String(children ?? "");
            // Devanagari (Hindi/Marathi/Sanskrit) text is never actual code — if the
            // model wraps a verse/transliteration in backticks anyway, render it as
            // plain bold text instead of a boxed code pill.
            const isDevanagariText = /[\u0900-\u097F]/.test(rawText);

            if (isInline && isDevanagariText) {
              return <strong className="font-semibold text-white">{children}</strong>;
            }

            return isInline ? (
              <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[0.85em] text-indigo-100" {...props}>
                {children}
              </code>
            ) : (
              <code className={`${className} font-mono text-xs`} {...props}>
                {children}
              </code>
            );
          },

          pre: ({ children }) => (
            <pre className="my-4 overflow-x-auto rounded-lg border border-white/10 bg-[#08111f] p-4 text-slate-100">
              {children}
            </pre>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="font-medium text-indigo-300 underline decoration-indigo-300/40 underline-offset-4 hover:text-indigo-200"
            >
              {children}
            </a>
          ),
          strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
        }}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  );
}

export default function ChatPage() {
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [attachments, setAttachments] = useState<ConversationAttachment[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [searchingFiles, setSearchingFiles] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loadingConvo, setLoadingConvo] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  // Track active id in a ref so async callbacks always see the latest value
  const activeIdRef = useRef<number | null>(null);

  useEffect(() => {
    activeIdRef.current = activeId;
  }, [activeId]);

  // ── On mount: fetch list + first conversation in parallel ───────────────
  useEffect(() => {
    (async () => {
      setHistoryLoading(true);
      try {
        const { conversations: list } = await listConversations();
        setConversations(list);
        if (list.length > 0) {
          // Fire both state update and detail fetch simultaneously
          const first = list[0];
          setActiveId(first.id);
          activeIdRef.current = first.id;
          setLoadingConvo(true);
          const detail = await getConversation(first.id);
          setMessages(detail.messages);
          setAttachments(detail.attachments);
          setLoadingConvo(false);
        }
      } finally {
        setHistoryLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const openConversation = useCallback(async (id: number) => {
    if (activeIdRef.current === id) return; // already open, skip
    setActiveId(id);
    activeIdRef.current = id;
    setLoadingConvo(true);
    setMessages([]);
    setAttachments([]);
    try {
      const detail = await getConversation(id);
      // Guard: user may have clicked a different chat while this was loading
      if (activeIdRef.current === id) {
        setMessages(detail.messages);
        setAttachments(detail.attachments);
      }
    } finally {
      if (activeIdRef.current === id) setLoadingConvo(false);
    }
  }, []);

  // Refresh sidebar list without re-opening current convo
  const refreshHistory = useCallback(async (selectId?: number) => {
    const { conversations: list } = await listConversations();
    setConversations(list);
    if (selectId) openConversation(selectId);
  }, [openConversation]);

  async function handleNewChat() {
    const convo = await createConversation();
    setConversations((prev) => [convo, ...prev]);
    setActiveId(convo.id);
    activeIdRef.current = convo.id;
    setMessages([]);
    setAttachments([]);
  }

  async function handleDeleteConversation(id: number, e: React.MouseEvent) {
    e.stopPropagation();
    await deleteConversation(id);
    const remaining = conversations.filter((c) => c.id !== id);
    setConversations(remaining);
    if (activeIdRef.current === id) {
      if (remaining.length > 0) openConversation(remaining[0].id);
      else {
        setActiveId(null);
        activeIdRef.current = null;
        setMessages([]);
        setAttachments([]);
      }
    }
  }

  async function handleSend() {
    if (!input.trim()) return;
    let convoId = activeIdRef.current;

    if (!convoId) {
      const convo = await createConversation();
      setConversations((prev) => [convo, ...prev]);
      setActiveId(convo.id);
      activeIdRef.current = convo.id;
      convoId = convo.id;
    }

    const text = input.trim();
    const hasAttachments = attachments.length > 0;
    setInput("");
    setSending(true);
    setSearchingFiles(hasAttachments);

    // Optimistic user bubble
    setMessages((prev) => [
      ...prev,
      { id: Date.now(), role: "user", content: text, used_rag: false, used_file_context: false, sources: [], created_at: new Date().toISOString() },
    ]);

    try {
      const { user_message, assistant_message } = await sendConversationMessage(convoId, text);
      setMessages((prev) => [...prev.slice(0, -1), user_message, assistant_message]);
      refreshHistory(); // update sidebar title (auto-set from first message)
    } catch (err) {
      console.error("Send message failed:", err);
      setMessages((prev) => prev.slice(0, -1)); // remove optimistic bubble on error
    } finally {
      setSending(false);
      setSearchingFiles(false);
    }
  }

  async function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    let convoId = activeIdRef.current;
    if (!convoId) {
      const convo = await createConversation();
      setConversations((prev) => [convo, ...prev]);
      setActiveId(convo.id);
      activeIdRef.current = convo.id;
      setMessages([]);
      setAttachments([]);
      convoId = convo.id;
    }

    setUploading(true);
    try {
      const result = await uploadDocument(file, convoId);
      setAttachments((prev) => [
        {
          id: result.document_id,
          title: result.title,
          file_type: result.file_type ?? (file.type.startsWith("image/") ? "image" : "pdf"),
          chunk_count: result.chunk_count,
          uploaded_at: new Date().toISOString(),
        },
        ...prev,
      ]);
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Upload failed — check the backend console for details.");
    } finally {
      setUploading(false);
    }
  }

  async function previewAttachment(doc: ConversationAttachment) {
    const url = await getDocumentFileBlobUrl(doc.id);
    window.open(url, "_blank");
  }

  return (
    <div className="flex h-full text-slate-200">

      {/* ── Chat history rail ─────────────────────────────────────────── */}
      <div className="flex w-60 shrink-0 flex-col border-r border-white/5 bg-[#0a0e1a] p-3">
        <button
          onClick={handleNewChat}
          className="mb-3 flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-300 hover:bg-white/5 transition-colors"
        >
          <MessageSquarePlus size={16} />
          New chat
        </button>

        <div className="flex-1 space-y-0.5 overflow-y-auto">
          {historyLoading ? (
            // Skeleton shimmer while loading
            Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-9 rounded-lg bg-white/5 animate-pulse"
                style={{ opacity: 1 - i * 0.2 }}
              />
            ))
          ) : conversations.length === 0 ? (
            <p className="px-3 py-2 text-xs text-slate-500">No chats yet — say something below.</p>
          ) : (
            conversations.map((c) => (
              <div
                key={c.id}
                onClick={() => openConversation(c.id)}
                className={`group flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors ${
                  c.id === activeId
                    ? "bg-indigo-500/15 text-indigo-300"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                }`}
              >
                <span className="truncate">{c.title}</span>
                <button
                  onClick={(e) => handleDeleteConversation(c.id, e)}
                  className="ml-2 hidden shrink-0 text-slate-500 hover:text-red-400 group-hover:block"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ── Main chat area ────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col min-w-0">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 py-6">
          {loadingConvo ? (
            // Message skeletons
            <div className="mx-auto max-w-2xl space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className={`flex ${i % 2 === 0 ? "justify-start" : "justify-end"}`}>
                  <div
                    className="h-14 rounded-2xl bg-white/5 animate-pulse"
                    style={{ width: `${45 + i * 10}%` }}
                  />
                </div>
              ))}
            </div>
          ) : messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
              <Bot size={36} className="text-indigo-400/50" />
              <p className="text-slate-500 text-sm">
                Ask any question. Attach a PDF or photo with the + button and<br />
                the answer will be grounded in it.
              </p>
            </div>
          ) : (
            <div className="mx-auto max-w-4xl space-y-4">
              {messages.map((m) => (
                <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`rounded-2xl px-4 py-3 text-sm ${
                      m.role === "user"
                        ? "max-w-[75%] bg-indigo-600 text-white"
                        : "max-w-[min(100%,52rem)] bg-white/5 text-slate-200 ring-1 ring-white/10"
                    }`}
                  >
                    {m.role === "assistant" ? (
                      <>
                        {(m.used_file_context || m.used_rag) && (
                          <div className="mb-3 inline-flex rounded-full bg-indigo-400/20 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-indigo-200">
                            Using attached file context
                          </div>
                        )}
                        <MarkdownMessage content={m.content} />
                        {m.sources && m.sources.length > 0 && (
                          <div className="mt-4 border-t border-white/10 pt-3">
                            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                              Sources
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {m.sources.map((source) => (
                                <span
                                  key={source}
                                  className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-indigo-300/20 bg-indigo-300/10 px-2.5 py-1 text-[11px] font-medium text-indigo-100"
                                >
                                  <FileText size={12} className="shrink-0 text-indigo-300" />
                                  <span className="truncate">{source}</span>
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    ) : (
                      m.content
                    )}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="rounded-2xl bg-white/5 px-4 py-3">
                    {searchingFiles && (
                      <p className="mb-2 text-xs text-indigo-300">Searching attached documents...</p>
                    )}
                    <div className="flex items-center gap-1.5">
                      {[0, 1, 2].map((i) => (
                        <span
                          key={i}
                          className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce"
                          style={{ animationDelay: `${i * 0.15}s` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Input bar ────────────────────────────────────────────────── */}
        <div className="border-t border-white/5 p-4">
          <div className="mx-auto flex max-w-2xl items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={handleFileSelected}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              title="Attach a PDF or photo"
              className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-slate-200 disabled:opacity-40 transition-colors"
            >
              {uploading ? (
                <span className="h-4 w-4 block rounded-full border-2 border-slate-400 border-t-transparent animate-spin" />
              ) : (
                <Plus size={18} />
              )}
            </button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
              placeholder={uploading ? "Uploading…" : "Ask a doubt…"}
              className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-500 outline-none"
            />
            <button
              onClick={handleSend}
              disabled={sending || !input.trim()}
              className="rounded-lg bg-indigo-600 p-2 text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* ── Attachments panel ─────────────────────────────────────────── */}
      <div className="w-56 shrink-0 border-l border-white/5 bg-[#0a0e1a] p-4">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Files in this chat
        </h3>
        <div className="space-y-2">
          {attachments.map((doc) => (
            <button
              key={doc.id}
              onClick={() => previewAttachment(doc)}
              className="flex w-full items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-3 py-2 text-left text-xs text-slate-300 hover:bg-white/10 transition-colors"
            >
              {doc.file_type === "image" ? (
                <ImageIcon size={14} className="shrink-0 text-emerald-400" />
              ) : (
                <FileText size={14} className="shrink-0 text-red-400" />
              )}
              <span className="truncate">{doc.title}</span>
            </button>
          ))}
          {attachments.length === 0 && (
            <p className="text-xs text-slate-500 leading-relaxed">
              Nothing uploaded yet. Use the + button to attach study material.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

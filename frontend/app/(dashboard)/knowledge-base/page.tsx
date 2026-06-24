// LOCATION: app/(dashboard)/knowledge-base/page.tsx

"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useAuth } from "@/hooks/useAuth";
import { uploadDocument, listDocuments, deleteDocument } from "@/lib/api";

interface DocumentItem {
  id: number;
  title: string;
  source: string;
  uploaded_at: string;
  chunk_count: number;
  file_type?: "pdf" | "image";
}

export default function KnowledgeBasePage() {
  useAuth();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [docsError, setDocsError] = useState<string | null>(null);

  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<"idle" | "success" | "error">("idle");
  const [uploadMessage, setUploadMessage] = useState("");
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = useCallback(async () => {
    setLoadingDocs(true);
    setDocsError(null);
    try {
      const data = await listDocuments();
      setDocuments(data.documents ?? []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load documents.";
      setDocsError(msg);
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleFile = async (file: File) => {
    if (!file) return;
    if (!(file.type === "application/pdf" || file.type.startsWith("image/"))) {
      setUploadStatus("error");
      setUploadMessage("Only PDF and image files are supported.");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setUploadStatus("error");
      setUploadMessage("File must be under 20 MB.");
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadStatus("idle");
    setUploadMessage("");

    // Simulate progress while the real upload runs
    const interval = setInterval(() => {
      setUploadProgress((p) => (p < 85 ? p + Math.random() * 12 : p));
    }, 400);

    try {
      const result = await uploadDocument(file);
      clearInterval(interval);
      setUploadProgress(100);
      setUploadStatus("success");
      setUploadMessage(
        `"${result.title}" uploaded â€” ${result.chunk_count} chunks indexed.`
      );
      await fetchDocuments();
    } catch (err: unknown) {
      clearInterval(interval);
      const msg = err instanceof Error ? err.message : "Upload failed.";
      setUploadStatus("error");
      setUploadMessage(msg);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
      setTimeout(() => {
        setUploadProgress(0);
        setUploadStatus("idle");
        setUploadMessage("");
      }, 4000);
    }
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [] // eslint-disable-line react-hooks/exhaustive-deps
  );

  const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(true);
  };

  const onDragLeave = () => setDragging(false);

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Delete failed.";
      alert(msg);
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });

  const formatSize = (chunks: number) =>
    chunks === 1 ? "1 chunk" : `${chunks} chunks`;

  return (
    <div className="min-h-screen bg-[#060d1f] p-8 space-y-8">
      {/* Ambient glows */}
      <div className="pointer-events-none fixed -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-blue-600/10 blur-[120px]" />
      <div className="pointer-events-none fixed bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-indigo-700/10 blur-[90px]" />

      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Knowledge Base</h1>
        <p className="text-slate-500 text-sm mt-1">
          Upload PDFs and images. PDFs are indexed for retrieval, while images are stored for preview and chat attachments.
        </p>
      </div>

      {/* Upload Zone */}
      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => !uploading && fileInputRef.current?.click()}
        className={`
          relative rounded-2xl border-2 border-dashed transition-all duration-200 cursor-pointer
          flex flex-col items-center justify-center gap-3 p-10 text-center
          ${dragging
            ? "border-blue-500 bg-blue-500/10 scale-[1.01]"
            : "border-white/10 bg-white/[0.03] hover:border-blue-500/50 hover:bg-white/[0.05]"
          }
          ${uploading ? "pointer-events-none" : ""}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,image/png,image/jpeg,image/webp"
          className="hidden"
          onChange={onFileChange}
        />

        {/* Icon */}
        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-1 transition-colors
          ${dragging ? "bg-blue-500/20" : "bg-white/[0.06]"}`}>
          <svg className={`w-7 h-7 ${dragging ? "text-blue-400" : "text-slate-400"}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.338-2.032A4.5 4.5 0 0 1 17.25 19.5H6.75Z" />
          </svg>
        </div>

        {uploading ? (
          <div className="w-full max-w-xs space-y-2">
            <p className="text-slate-300 text-sm font-medium">Uploading & indexingâ€¦</p>
            <div className="w-full bg-white/5 rounded-full h-2 overflow-hidden">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-blue-600 to-indigo-500 transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="text-slate-500 text-xs">{Math.round(uploadProgress)}%</p>
          </div>
        ) : (
          <>
            <p className="text-slate-300 font-medium">
              {dragging ? "Drop your PDF here" : "Drag & drop a PDF or image, or click to browse"}
            </p>
            <p className="text-slate-600 text-xs">PDF/image · max 20 MB</p>
          </>
        )}

        {/* Status message */}
        {uploadStatus !== "idle" && (
          <div className={`mt-1 text-xs px-3 py-1.5 rounded-lg font-medium
            ${uploadStatus === "success"
              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
              : "bg-red-500/10 text-red-400 border border-red-500/20"
            }`}>
            {uploadStatus === "success" ? "âœ“ " : "âœ• "}{uploadMessage}
          </div>
        )}
      </div>

      {/* Documents List */}
      <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-white">Uploaded Documents</h2>
          {!loadingDocs && (
            <span className="text-xs text-slate-500 bg-white/[0.05] border border-white/10 px-2.5 py-1 rounded-full">
              {documents.length} {documents.length === 1 ? "file" : "files"}
            </span>
          )}
        </div>

        {loadingDocs ? (
          <div className="flex items-center gap-2 text-slate-500 text-sm py-4">
            <svg className="animate-spin h-4 w-4 text-blue-500" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            Loading your documentsâ€¦
          </div>
        ) : docsError ? (
          <p className="text-red-400 text-sm">{docsError}</p>
        ) : documents.length === 0 ? (
          <div className="text-center py-10 space-y-2">
            <p className="text-slate-500 text-sm">No documents yet.</p>
            <p className="text-slate-600 text-xs">Upload a PDF or image above to get started.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center gap-4 bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 group hover:bg-white/[0.06] transition-colors duration-150"
              >
                {/* PDF icon */}
                <div className="w-9 h-9 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center shrink-0">
                  <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round"
                      d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                  </svg>
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-slate-200 text-sm font-medium truncate">{doc.title}</p>
                  <p className="text-slate-600 text-xs mt-0.5">
                    {formatSize(doc.chunk_count)} Â· {formatDate(doc.uploaded_at)}
                  </p>
                </div>

                {/* Chunk badge */}
                <span className="text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded-full shrink-0 hidden sm:block">
                  {doc.chunk_count} chunks
                </span>

                {/* Delete */}
                <button
                  onClick={() => handleDelete(doc.id)}
                  disabled={deletingId === doc.id}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-colors duration-150 shrink-0"
                  title="Delete document"
                >
                  {deletingId === doc.id ? (
                    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round"
                        d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                    </svg>
                  )}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info card */}
      <div className="bg-blue-500/5 border border-blue-500/15 rounded-2xl p-5 flex gap-3">
        <svg className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
        </svg>
        <div className="space-y-1">
          <p className="text-blue-300 text-sm font-medium">How this works</p>
          <p className="text-slate-500 text-xs leading-relaxed">
            Uploaded PDFs are split into chunks and indexed. Uploaded images are stored for retrieval and preview. When you ask the AI Tutor a question,
            it searches your documents first. If relevant content is found, the answer is grounded
            in your material â€” and the chat will show a <span className="text-blue-400">"Using your study material"</span> badge.
          </p>
        </div>
      </div>
    </div>
  );
}


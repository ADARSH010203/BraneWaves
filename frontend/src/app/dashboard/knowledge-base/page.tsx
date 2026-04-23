"use client";
import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import { FileText, UploadCloud, Trash2, Library, AlertCircle, File, Sparkles, Search } from "lucide-react";
import { formatCost } from "@/lib/utils"; 

const formatSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export default function KnowledgeBasePage() {
  const [docs, setDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragActive, setDragActive] = useState(false);
  
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const filteredDocs = docs.filter(d => {
    const matchSearch = d.original_name?.toLowerCase().includes(search.toLowerCase()) || d.filename?.toLowerCase().includes(search.toLowerCase());
    const ext = d.filename?.split('.').pop()?.toLowerCase() || "";
    const matchType = typeFilter === "all" || ext === typeFilter || d.content_type?.includes(typeFilter);
    return matchSearch && matchType;
  });

  const fetchDocs = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.getKBDocuments();
      setDocs(res);
    } catch (err: any) {
      setError(err.message || "Failed to load knowledge base");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const processFile = async (file: File) => {
    if (file.size > 50 * 1024 * 1024) {
      setError("File exceeds 50MB limit");
      return;
    }
    setError("");
    setUploading(true);
    try {
      await api.uploadKBFile(file);
      await fetchDocs();
    } catch (err: any) {
      setError(err.message || "Failed to upload file");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await processFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      await processFile(e.target.files[0]);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteKBDocument(id);
      setDocs(docs.filter(d => d.id !== id));
    } catch (err: any) {
      setError(err.message || "Failed to delete document");
    }
  };

  return (
    <div className="max-w-5xl mx-auto animate-fade-in relative z-10 w-full">
      <div className="mb-10">
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
          Knowledge Base <Library className="h-6 w-6 text-brand-400" />
        </h1>
        <p className="text-slate-400">
          Upload reference documents, style guides, or manuals here. Vector Agent will automatically query these files 
          to retrieve contextual ground-truth data during tasks.
        </p>
      </div>

      {error && (
        <motion.div initial={{opacity:0, y:-10}} animate={{opacity:1, y:0}}
          className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm mb-6">
          <AlertCircle className="h-4 w-4" />{error}
        </motion.div>
      )}

      {/* Filters & Search */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search documents..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="input-field pl-10"
          />
        </div>
        <div className="flex gap-2 overflow-x-auto pb-2 sm:pb-0">
          {["all", "pdf", "docx", "csv", "txt"].map(type => (
            <button
              key={type}
              onClick={() => setTypeFilter(type)}
              className={`px-3 py-2 rounded-xl text-xs font-medium transition uppercase ${
                typeFilter === type
                  ? "bg-brand-500/20 text-brand-300 border border-brand-500/30"
                  : "text-slate-400 border border-white/10 hover:border-white/20"
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>
      {(search || typeFilter !== 'all') && (
        <p className="text-xs text-slate-500 mb-6 font-medium">
          Showing {filteredDocs.length} of {docs.length} documents
        </p>
      )}

      {/* Upload Zone */}
      <div 
        onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-2xl p-10 text-center transition-all bg-slate-900/50 mb-10 ${
          dragActive ? "border-brand-500 bg-brand-500/10" : "border-white/10 hover:border-brand-500/30 hover:bg-slate-800/80"
        }`}
      >
        <input type="file" onChange={handleChange} accept=".pdf,.txt,.md,.mdx,.csv"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" />
        
        <div className="flex flex-col items-center justify-center pointer-events-none">
          {uploading ? (
            <>
              <div className="h-12 w-12 border-4 border-brand-500/30 border-t-brand-500 rounded-full animate-spin mb-4" />
              <p className="font-bold text-white text-lg">Encrypting & Vectorizing...</p>
              <p className="text-sm text-slate-500 mt-1">Parsing text chunks to database</p>
            </>
          ) : (
            <>
              <div className={`p-4 rounded-full mb-4 transition-colors ${dragActive ? "bg-brand-500/20" : "bg-slate-800"}`}>
                 <UploadCloud className={`h-8 w-8 ${dragActive ? "text-brand-400" : "text-slate-400"}`} />
              </div>
              <p className="font-bold text-white text-lg mb-1">
                Drag & Drop files here or <span className="text-brand-400">Browse</span>
              </p>
              <p className="text-sm text-slate-500">Supports PDF, TXT, MD, CSV (Max 50MB)</p>
            </>
          )}
        </div>
      </div>

      {/* Document Vault */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-5 border-b border-white/10 bg-slate-900/50 flex items-center justify-between">
          <div className="flex items-center gap-3">
             <FileText className="h-5 w-5 text-brand-400" />
             <h2 className="font-bold text-white">Your Vault</h2>
          </div>
          <span className="text-xs font-mono px-2 py-1 bg-slate-800 rounded-md text-slate-400">{docs.length} Documents</span>
        </div>

        {loading && docs.length === 0 ? (
          <div className="p-16 text-center text-slate-500">
             <div className="w-6 h-6 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin mx-auto mb-4" />
             Loading vault...
          </div>
        ) : docs.length === 0 ? (
          <div className="p-16 text-center">
            <Sparkles className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-white mb-2">Knowledge Base is Empty</h3>
            <p className="text-slate-400">Upload documents above to augment agents with local knowledge.</p>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            <p>No documents match your filters</p>
            <button onClick={() => { setSearch(""); setTypeFilter("all"); }} className="text-brand-400 text-sm mt-2 hover:underline">
              Clear filters
            </button>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            <AnimatePresence>
              {filteredDocs.map((doc, i) => (
                <motion.div key={doc.id} initial={{opacity:0, height:0}} animate={{opacity:1, height:"auto"}} exit={{opacity:0, height:0}}
                  className="px-6 py-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors group">
                  <div className="flex items-center gap-4 min-w-0 flex-1">
                    <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center shrink-0 border border-indigo-500/20">
                      <File className="h-5 w-5 text-indigo-400" />
                    </div>
                    <div className="min-w-0 pr-4">
                      <p className="font-bold text-sm text-slate-200 truncate">{doc.filename || doc.original_name}</p>
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                          doc.is_indexed
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}>
                          {doc.is_indexed ? "Indexed" : "Processing..."}
                        </span>
                        <span className="text-xs text-slate-500">• {formatSize(doc.size_bytes)}</span>
                        <span className="text-xs text-slate-500 hidden sm:inline">• Added {new Date(doc.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                  <button onClick={() => handleDelete(doc.id)}
                    className="p-2 rounded-lg text-slate-500 hover:bg-red-500/10 hover:text-red-400 transition-all opacity-0 group-hover:opacity-100">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";
import { motion } from "framer-motion";

export function TaskCardSkeleton() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="glass-card p-6 flex flex-col justify-between h-[200px]"
    >
      <div className="space-y-4">
        <div className="flex justify-between items-start">
          <div className="w-3/4 h-6 bg-slate-700/50 rounded-lg animate-pulse" />
          <div className="w-16 h-6 bg-slate-700/50 rounded-full animate-pulse" />
        </div>
        <div className="space-y-2">
          <div className="w-full h-4 bg-slate-800/50 rounded animate-pulse" />
          <div className="w-5/6 h-4 bg-slate-800/50 rounded animate-pulse" />
        </div>
      </div>
      <div className="mt-4 pt-4 border-t border-white/10 flex justify-between">
        <div className="w-24 h-4 bg-slate-800/50 rounded animate-pulse" />
        <div className="w-20 h-4 bg-slate-800/50 rounded animate-pulse" />
      </div>
    </motion.div>
  );
}

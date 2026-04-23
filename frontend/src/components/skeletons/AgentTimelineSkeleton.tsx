"use client";
import { motion } from "framer-motion";

export function AgentTimelineSkeleton() {
  return (
    <div className="relative border-l-2 border-slate-700/50 ml-4 space-y-6 pb-4 pt-2">
      {[1, 2, 3].map((i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.1 }}
          className="relative pl-8"
        >
          {/* Timeline Node */}
          <div className="absolute -left-[11px] top-1.5 w-5 h-5 rounded-full border-4 border-slate-900 bg-slate-700/50 animate-pulse" />
          
          <div className="bg-slate-800/20 border border-white/5 rounded-xl p-4">
            <div className="flex flex-wrap items-center gap-3 mb-3">
              <div className="w-6 h-4 bg-slate-700/50 rounded animate-pulse" />
              <div className="w-24 h-6 bg-slate-700/50 rounded-lg animate-pulse" />
              <div className="w-16 h-5 bg-slate-700/50 rounded animate-pulse" />
            </div>
            <div className="w-3/4 h-5 bg-slate-700/50 rounded animate-pulse" />
          </div>
        </motion.div>
      ))}
    </div>
  );
}

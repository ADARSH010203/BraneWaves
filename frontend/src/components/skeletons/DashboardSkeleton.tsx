"use client";
import { motion } from "framer-motion";

export function DashboardSkeleton() {
  return (
    <div className="space-y-8 animate-fade-in relative z-10 w-full max-w-7xl mx-auto px-4 md:px-0">
      {/* Header Skeleton */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="w-64 h-10 bg-slate-800/50 rounded-lg animate-pulse mb-2" />
          <div className="w-96 h-5 bg-slate-800/50 rounded-md animate-pulse" />
        </div>
        <div className="w-40 h-10 bg-brand-500/20 rounded-xl animate-pulse" />
      </div>

      {/* Filters Skeleton */}
      <div className="glass-card p-4 flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="flex gap-2 w-full sm:w-auto overflow-x-auto">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="w-24 h-8 bg-slate-800/50 rounded-full animate-pulse shrink-0" />
          ))}
        </div>
        <div className="w-full sm:w-64 h-10 bg-slate-800/50 rounded-xl animate-pulse" />
      </div>

      {/* Grid Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
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
        ))}
      </div>
    </div>
  );
}

export default function DashboardLoading() {
  return (
    <div className="flex-1 p-6 space-y-6">
      {/* Header skeleton */}
      <div className="animate-pulse">
        <div className="h-8 w-48 bg-slate-200 dark:bg-slate-800 rounded-lg mb-2" />
        <div className="h-4 w-72 bg-slate-100 dark:bg-slate-800/60 rounded" />
      </div>

      {/* Metric cards skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-100 dark:border-slate-800 p-5 animate-pulse"
          >
            <div className="h-4 w-24 bg-slate-100 dark:bg-slate-800 rounded mb-3" />
            <div className="h-8 w-32 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
            <div className="h-3 w-16 bg-slate-100 dark:bg-slate-800 rounded" />
          </div>
        ))}
      </div>

      {/* Content area skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-2xl border border-slate-100 dark:border-slate-800 p-5 h-64 animate-pulse">
          <div className="h-5 w-32 bg-slate-200 dark:bg-slate-700 rounded mb-4" />
          <div className="h-40 bg-slate-100 dark:bg-slate-800 rounded-xl" />
        </div>
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-100 dark:border-slate-800 p-5 h-64 animate-pulse">
          <div className="h-5 w-24 bg-slate-200 dark:bg-slate-700 rounded mb-4" />
          <div className="h-40 bg-slate-100 dark:bg-slate-800 rounded-xl" />
        </div>
      </div>
    </div>
  );
}

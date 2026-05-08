export default function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-slate-950">
      <div className="flex flex-col items-center gap-6">
        <div className="relative">
          <div className="w-16 h-16 rounded-2xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-600/25">
            <span className="text-white font-black text-2xl">C</span>
          </div>
          <div className="absolute -inset-1 rounded-2xl border-2 border-blue-600/30 animate-ping" />
        </div>
        <div className="flex gap-1.5 items-center">
          <div
            className="w-2 h-2 rounded-full bg-blue-600 animate-bounce"
            style={{ animationDelay: '0ms' }}
          />
          <div
            className="w-2 h-2 rounded-full bg-blue-600 animate-bounce"
            style={{ animationDelay: '150ms' }}
          />
          <div
            className="w-2 h-2 rounded-full bg-blue-600 animate-bounce"
            style={{ animationDelay: '300ms' }}
          />
        </div>
        <p className="text-sm font-medium text-slate-400 uppercase tracking-widest">Loading</p>
      </div>
    </div>
  );
}

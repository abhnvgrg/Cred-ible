export default function Loading() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 w-full">
      <div className="relative w-16 h-16 flex items-center justify-center">
        <svg 
          className="absolute inset-0 w-full h-full animate-[spin_2s_linear_infinite] text-indigo-500/80" 
          viewBox="0 0 100 100"
        >
          <circle 
            cx="50" cy="50" r="44" 
            fill="transparent" 
            stroke="currentColor" 
            strokeWidth="8" 
            strokeDasharray="200" 
            strokeLinecap="round" 
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-2.5 h-2.5 bg-indigo-400 rounded-full animate-ping" />
        </div>
      </div>
      <p className="text-xs text-indigo-300/80 font-bold tracking-[0.2em] uppercase animate-pulse">
        Processing Request
      </p>
    </div>
  );
}

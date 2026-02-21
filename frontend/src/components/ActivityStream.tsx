import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { STREAM_TYPES } from "@/lib/api";
import { mockStreamEvents } from "@/lib/mock-data";

interface StreamEvent {
  type: string;
  message: string;
  timestamp: string;
}

export default function ActivityStream() {
  const [events, setEvents] = useState<StreamEvent[]>(mockStreamEvents);
  const containerRef = useRef<HTMLDivElement>(null);

  // Try SSE, fall back to mock
  useEffect(() => {
    let es: EventSource | null = null;
    try {
      es = new EventSource("http://localhost:8000/api/agent/stream");
      es.onmessage = (e) => {
        const event = JSON.parse(e.data);
        setEvents((prev) => [event, ...prev].slice(0, 50));
      };
      es.onerror = () => {
        es?.close();
        // Keep mock data
      };
    } catch {
      // Keep mock data
    }
    return () => es?.close();
  }, []);

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  };

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-score-green pulse-green" />
        <h3 className="text-sm font-semibold text-foreground">Live Activity</h3>
        <span className="ml-auto text-[10px] text-muted-foreground font-mono">{events.length} events</span>
      </div>
      <div ref={containerRef} className="max-h-[600px] overflow-y-auto scrollbar-thin p-2 space-y-0.5">
        <AnimatePresence initial={false}>
          {events.map((event, i) => (
            <motion.div
              key={`${event.timestamp}-${i}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25 }}
              className="flex items-start gap-2 px-2 py-1.5 rounded-lg hover:bg-secondary/50 transition-colors"
            >
              <span className="text-sm shrink-0">{STREAM_TYPES[event.type] || "📋"}</span>
              <div className="min-w-0 flex-1">
                <p className="text-xs text-foreground/80 leading-relaxed">{event.message}</p>
                <span className="text-[10px] font-mono text-muted-foreground">{formatTime(event.timestamp)}</span>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

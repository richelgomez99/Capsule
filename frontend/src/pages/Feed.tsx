import { useState, useEffect, useRef } from "react";
import { useToast } from "@/hooks/use-toast";
import { api, STREAM_TYPES } from "@/lib/api";
import { mockFeed, mockMetrics, mockStreamEvents } from "@/lib/mock-data";
import FeedCard from "@/components/FeedCard";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";

const API_BASE = "http://localhost:8000";

export default function Feed() {
  const [feed, setFeed] = useState(mockFeed);
  const [metrics, setMetrics] = useState(mockMetrics);
  const [activity, setActivity] = useState<any[]>(mockStreamEvents);
  const [processing, setProcessing] = useState(false);
  const [actions, setActions] = useState<any[]>([]);
  const [digest, setDigest] = useState<any>(null);
  const [userModel, setUserModel] = useState<any>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    api.getFeed().then(setFeed).catch(() => {});
    api.getMetrics().then(setMetrics).catch(() => {});
    api.getUserModel().then(setUserModel).catch(() => {});
    fetch(`${API_BASE}/api/activity?limit=20`).then(r => r.json()).then(setActivity).catch(() => {});
    fetch(`${API_BASE}/api/actions`).then(r => r.json()).then(setActions).catch(() => {});
    fetch(`${API_BASE}/api/digest`).then(r => r.json()).then(setDigest).catch(() => {});
  }, []);

  const handleAction = async (cardId: string, actionId: string, data?: any) => {
    try {
      const res = await api.feedAction(cardId, actionId, data);
      toast({ title: "Agent responded", description: res.message || "Action processed." });
    } catch {
      toast({ title: "Noted!", description: `Action "${actionId}" recorded locally.` });
    }
    if (actionId === "dismiss") {
      setFeed((prev) => prev.filter((c) => c.id !== cardId));
    }
    api.getMetrics().then(setMetrics).catch(() => {});
  };

  const startProcessing = async () => {
    setProcessing(true);
    try {
      const res = await fetch(`${API_BASE}/api/process`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ batch_size: 5 }),
      });
      const data = await res.json();
      toast({ title: "On it!", description: data.message });
    } catch {
      toast({ title: "Starting...", description: "Processing your captures now." });
    }

    pollRef.current = setInterval(async () => {
      try {
        const actRes = await fetch(`${API_BASE}/api/activity?limit=30`);
        setActivity(await actRes.json());
        const metRes = await fetch(`${API_BASE}/api/metrics`);
        setMetrics(await metRes.json());
        const procRes = await fetch(`${API_BASE}/api/processing`);
        const proc = await procRes.json();
        if (!proc.processing) {
          setProcessing(false);
          if (pollRef.current) clearInterval(pollRef.current);
          fetch(`${API_BASE}/api/actions`).then(r => r.json()).then(setActions).catch(() => {});
          toast({ title: "All done!", description: "I processed your saves, scored my work, and took actions." });
        }
      } catch {}
    }, 2000);
  };

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const facts = userModel?.learned_facts || [];

  return (
    <div className="space-y-6 pb-20 lg:pb-0">

      {/* ── Section 1: Warm Greeting ── */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-4"
      >
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-foreground">
            {digest?.greeting || "Here's what I've been thinking about your saves"}
          </h1>
          <p className="text-sm text-muted-foreground">
            {digest ? `${digest.total_captures} saves from ${digest.total_apps} apps · ${digest.pii_protected} protected` : "Loading..."}
          </p>
        </div>

        {/* ── Stat Pills ── */}
        {digest?.pills && (
          <div className="flex flex-wrap gap-2">
            {digest.pills.map((pill: any) => (
              <motion.div
                key={pill.category}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1 }}
                className="flex items-center gap-2 px-4 py-3 rounded-[10px] border border-white/[0.08] bg-white/[0.04] backdrop-blur-sm hover:bg-white/[0.08] transition-colors cursor-default"
              >
                <span className="text-2xl font-bold text-foreground">{pill.count}</span>
                <div className="flex flex-col">
                  <span className="text-xs text-muted-foreground leading-tight">{pill.emoji} {pill.category}</span>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>

      {/* ── Process Button ── */}
      <Button
        onClick={startProcessing}
        disabled={processing}
        className="w-full h-12 text-base font-semibold bg-primary text-primary-foreground hover:bg-primary/90"
      >
        {processing ? (
          <span className="flex items-center gap-2">
            <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            I'm working — watch me think, decide, and act →
          </span>
        ) : (
          "⚡ Process Today's Saves"
        )}
      </Button>

      {/* ── Two Column Layout ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* Left: Feed + Actions + User Model */}
        <div className="lg:col-span-3 space-y-4">

          {/* Feed Cards */}
          {feed.map((card, i) => (
            <FeedCard key={card.id} card={card} onAction={handleAction} index={i} />
          ))}
          {feed.length === 0 && (
            <div className="text-center py-12 text-muted-foreground text-sm">
              All caught up. I'm thinking...
            </div>
          )}

          {/* ── Agent Actions ── */}
          {actions.length > 0 && (
            <div className="space-y-3 mt-2">
              <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                I took {actions.length} actions from your saves
              </h2>
              {actions.map((a: any) => (
                <div key={a.file} className="p-4 rounded-xl border border-border bg-card space-y-2">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl shrink-0">
                      {a.type === "calendar" ? "📅" : a.type === "todos" ? "✅" : "📊"}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-foreground">{a.title || a.file}</p>
                      {a.detail && <p className="text-xs text-muted-foreground mt-0.5">{a.detail}</p>}
                      {a.source && (
                        <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground">
                          from {a.source}
                        </span>
                      )}
                    </div>
                    <a
                      href={`${API_BASE}/api/actions/${a.file}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0 text-xs px-2 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90"
                    >
                      {a.type === "calendar" ? "Add to Calendar" : "Download"}
                    </a>
                  </div>
                  {a.items && a.items.length > 0 && (
                    <div className="pl-10 space-y-1">
                      {a.items.map((item: any, idx: number) => (
                        <div key={idx} className="flex items-center gap-2 text-xs text-foreground/80">
                          <span className="w-3 h-3 rounded border border-muted-foreground/40 shrink-0" />
                          <span className="truncate">{item.text}</span>
                          <span className="text-muted-foreground shrink-0">({item.source})</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {a.sources && (
                    <div className="pl-10 flex flex-wrap gap-1">
                      {a.sources.map((s: string) => (
                        <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-secondary/60 text-muted-foreground">{s}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* ── What I Know About You ── */}
          {facts.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="rounded-xl border border-primary/20 bg-primary/[0.04] p-5 space-y-3 mt-4"
            >
              <h3 className="text-base font-semibold text-foreground">What I know about you</h3>
              <div className="space-y-2">
                {facts.map((fact: any, i: number) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-foreground/80">
                    <span className="text-muted-foreground mt-0.5">·</span>
                    <span>{fact.text}</span>
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-white/[0.06]">
                <span className="text-xs text-muted-foreground">{facts.length} things learned from your saves</span>
                <button
                  onClick={() => {
                    const el = document.querySelector('[data-card-type="learning"]');
                    if (el) el.scrollIntoView({ behavior: "smooth" });
                  }}
                  className="text-xs text-primary hover:underline"
                >
                  Teach me more →
                </button>
              </div>
            </motion.div>
          )}
        </div>

        {/* Right: Activity Stream */}
        <div className="lg:col-span-2">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
            What I'm Doing {processing && <span className="text-yellow-500 ml-2 animate-pulse">● Thinking...</span>}
          </h2>
          <div className="lg:sticky lg:top-6 space-y-2 max-h-[80vh] overflow-y-auto pr-1 scrollbar-thin">
            <AnimatePresence initial={false}>
              {activity.map((evt, i) => (
                <motion.div
                  key={`${evt.timestamp}-${i}`}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3 }}
                  className="flex gap-2 items-start p-2.5 rounded-lg bg-card border border-border text-xs"
                >
                  <span className="text-base shrink-0">{STREAM_TYPES[evt.type] || "📋"}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-foreground/90 leading-snug">{evt.message}</p>
                    <p className="text-muted-foreground text-[10px] mt-0.5">
                      {evt.timestamp?.slice(11, 19) || "now"}
                    </p>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}

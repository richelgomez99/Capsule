import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { mockJudgePanel, mockMetrics, mockStreamEvents } from "@/lib/mock-data";

export default function JudgePanel() {
  const [panel, setPanel] = useState(mockJudgePanel);
  const [metrics, setMetrics] = useState(mockMetrics);

  useEffect(() => {
    api.getJudgePanel().then(setPanel).catch(() => {});
    api.getMetrics().then(setMetrics).catch(() => {});
  }, []);

  return (
    <div className="space-y-8 pb-20 lg:pb-0">
      <div>
        <h1 className="text-xl font-semibold text-foreground">🏆 Judge Panel</h1>
        <p className="text-sm text-muted-foreground mt-1">Technical architecture & self-improvement overview</p>
      </div>

      {/* Architecture */}
      <Section title="Architecture">
        <div className="flex flex-col items-center gap-4">
          <ArchNode label={panel.architecture.coordinator} primary />
          <div className="w-px h-6 bg-border" />
          <div className="flex flex-wrap justify-center gap-3">
            {panel.architecture.agents.map((a: string) => (
              <ArchNode key={a} label={a} />
            ))}
          </div>
          <div className="w-px h-6 bg-border" />
          <div className="text-xs text-muted-foreground text-center">ProcessCapture Pipeline</div>
          <div className="flex items-center gap-2 flex-wrap justify-center">
            {panel.architecture.pipeline.map((step: string, i: number) => (
              <span key={step} className="flex items-center gap-2">
                <span className="px-3 py-1.5 rounded-lg bg-secondary text-xs font-medium text-foreground">{step}</span>
                {i < panel.architecture.pipeline.length - 1 && <span className="text-muted-foreground">→</span>}
              </span>
            ))}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-[10px] text-muted-foreground">Quality Loop:</span>
            {panel.architecture.quality_loop.map((step: string, i: number) => (
              <span key={step} className="flex items-center gap-1">
                <span className="px-2 py-1 rounded bg-primary/10 text-[10px] font-mono text-primary">{step}</span>
                {i < panel.architecture.quality_loop.length - 1 && <span className="text-muted-foreground text-xs">→</span>}
              </span>
            ))}
            <span className="text-muted-foreground text-xs">↩</span>
          </div>
        </div>
      </Section>

      {/* Sponsors */}
      <Section title="Powered By">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {panel.sponsors.map((s: any, i: number) => (
            <motion.div
              key={s.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="rounded-xl border border-border bg-card p-4 text-center card-hover"
            >
              <span className="text-3xl">{s.logo}</span>
              <h3 className="font-semibold text-foreground mt-2">{s.name}</h3>
              <p className="text-xs text-primary mt-0.5">{s.product}</p>
              <p className="text-xs text-muted-foreground mt-2">{s.description}</p>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* Self-Improvement Loops */}
      <Section title="Self-Improvement Loops">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {panel.improvement_loops.map((loop: any, i: number) => (
            <motion.div
              key={loop.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="rounded-xl border border-border bg-card p-4 card-hover"
            >
              <h3 className="font-semibold text-foreground text-sm">{loop.name}</h3>
              <p className="text-xs text-muted-foreground mt-1">{loop.description}</p>
              <p className="text-xs text-foreground/70 mt-2 italic">{loop.how}</p>
              <Badge variant="secondary" className="mt-3 text-[10px] font-mono">{loop.metric}</Badge>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* Live Metrics */}
      <Section title="Live Metrics">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
          <MetricCard label="Captures" value={metrics.total_captures} />
          <MetricCard label="Reflections" value={metrics.reflections_triggered} />
          <MetricCard label="PII Caught" value={metrics.pii_caught} accent />
          <MetricCard label="Facts Learned" value={metrics.facts_learned} />
          <MetricCard label="Corrections" value={metrics.corrections_applied} />
          <MetricCard label="Avg Confidence" value={`${metrics.avg_confidence}%`} />
        </div>

        {/* Score Trend Chart */}
        <div className="rounded-xl border border-border bg-card p-4">
          <h3 className="text-sm font-semibold text-foreground mb-4">Score Trend</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={metrics.score_trend}>
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(240 4% 46%)" }} axisLine={false} tickLine={false} />
              <YAxis domain={[0.5, 1]} tick={{ fontSize: 10, fill: "hsl(240 4% 46%)" }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{
                  background: "hsl(240 15% 8%)",
                  border: "1px solid hsl(240 5% 15%)",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Line type="monotone" dataKey="score" stroke="hsl(36, 90%, 55%)" strokeWidth={2} dot={{ fill: "hsl(36, 90%, 55%)", r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Section>

      {/* Activity Log */}
      <Section title="Recent Activity">
        <div className="rounded-xl border border-border bg-card divide-y divide-border max-h-[400px] overflow-y-auto scrollbar-thin">
          {mockStreamEvents.map((event, i) => (
            <div key={i} className="px-4 py-2.5 flex items-center gap-3 text-xs">
              <span>{{"AIRIA":"🧠","CAPTURE":"🏷️","DLP":"🛡️","BRAINTRUST":"📊","REFLECTION":"🔄","SYNTHESIS":"💡","QUESTION":"❓"}[event.type] || "📋"}</span>
              <span className="text-foreground/80 flex-1">{event.message}</span>
              <span className="text-muted-foreground font-mono shrink-0">
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">{title}</h2>
      {children}
    </section>
  );
}

function ArchNode({ label, primary }: { label: string; primary?: boolean }) {
  return (
    <div className={`px-4 py-2 rounded-lg text-xs font-mono ${primary ? "bg-primary/15 text-primary border border-primary/30" : "bg-secondary text-foreground"}`}>
      {label}
    </div>
  );
}

function MetricCard({ label, value, accent }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-card p-3 text-center">
      <div className={`text-xl font-semibold font-mono ${accent ? "text-pii" : "text-foreground"}`}>{value}</div>
      <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">{label}</div>
    </div>
  );
}

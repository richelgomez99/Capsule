import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { User, Lightbulb, HelpCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { mockUserModel } from "@/lib/mock-data";

export default function AboutMe() {
  const [model, setModel] = useState(mockUserModel);

  useEffect(() => {
    api.getUserModel().then(setModel).catch(() => {});
  }, []);

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      <h1 className="text-xl font-semibold text-foreground flex items-center gap-2">
        <User size={20} className="text-primary" />
        What the Agent Knows About You
      </h1>

      {/* Profile card */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-xl border border-border bg-card p-5 space-y-4"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Role" value={model.role} />
          <Field label="Work Context" value={model.work_context} />
        </div>
        <div>
          <span className="text-xs text-muted-foreground uppercase tracking-wider">Languages</span>
          <div className="flex gap-2 mt-1">
            {model.languages.map((l: string) => (
              <Badge key={l} variant="secondary" className="text-xs">{l}</Badge>
            ))}
          </div>
        </div>
        <div>
          <span className="text-xs text-muted-foreground uppercase tracking-wider">Interests</span>
          <div className="flex gap-2 mt-1 flex-wrap">
            {model.interests.map((i: string) => (
              <Badge key={i} variant="outline" className="text-xs border-primary/30 text-primary">{i}</Badge>
            ))}
          </div>
        </div>
        <div>
          <span className="text-xs text-muted-foreground uppercase tracking-wider">Active Projects</span>
          <div className="flex gap-2 mt-1 flex-wrap">
            {model.active_projects.map((p: string) => (
              <span key={p} className="text-sm text-foreground/80">{p}</span>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Confidence meters */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          📊 Classification Confidence
        </h2>
        <div className="space-y-3">
          {Object.entries(model.confidence).sort(([, a], [, b]) => (b as number) - (a as number)).map(([cat, val]) => (
            <div key={cat} className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-28 capitalize">{cat}</span>
              <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${val}%` }}
                  transition={{ duration: 0.8, delay: 0.1 }}
                  className="h-full bg-primary rounded-full"
                />
              </div>
              <span className="text-xs font-mono text-foreground w-10 text-right">{val}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* Learned Facts */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <Lightbulb size={16} className="text-primary" />
          Learned Facts ({model.learned_facts.length})
        </h2>
        <div className="space-y-2">
          {model.learned_facts.map((fact: any, i: number) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-start gap-3 p-2 rounded-lg hover:bg-secondary/50 transition-colors"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
              <div>
                <p className="text-sm text-foreground">{fact.text}</p>
                <span className="text-[10px] text-muted-foreground">
                  {fact.source} · {new Date(fact.timestamp).toLocaleDateString()}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Pending Questions */}
      {model.pending_questions.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <HelpCircle size={16} className="text-info" />
            Questions for You
          </h2>
          <div className="space-y-3">
            {model.pending_questions.map((q: string, i: number) => (
              <div key={i} className="p-3 rounded-lg bg-secondary flex items-center gap-3">
                <span className="text-lg">❓</span>
                <p className="text-sm text-foreground flex-1">{q}</p>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" className="text-xs h-7">Answer</Button>
                  <Button variant="ghost" size="sm" className="text-xs h-7 text-muted-foreground">Skip</Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-xs text-muted-foreground uppercase tracking-wider">{label}</span>
      <p className="text-sm text-foreground mt-0.5">{value}</p>
    </div>
  );
}

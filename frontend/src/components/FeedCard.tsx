import { useState } from "react";
import { motion } from "framer-motion";
import { FEED_TYPES } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface FeedCardProps {
  card: {
    id: string;
    type: string;
    title: string;
    body: string;
    reasoning: string;
    actions: { id: string; label: string }[];
  };
  onAction: (cardId: string, actionId: string, data?: any) => void;
  index: number;
}

const accentColors: Record<string, string> = {
  protection: "bg-feed-protection",
  insight: "bg-feed-insight",
  learning: "bg-feed-learning",
  captured: "bg-feed-captured",
  forgotten: "bg-feed-forgotten",
  synthesis: "bg-feed-synthesis",
};

export default function FeedCard({ card, onAction, index }: FeedCardProps) {
  const meta = FEED_TYPES[card.type] || { emoji: "📋", label: card.type };
  const [showCustom, setShowCustom] = useState(false);
  const [customValue, setCustomValue] = useState("");

  const isLearning = card.type === "learning";

  const handleCustomSubmit = () => {
    if (customValue.trim()) {
      onAction(card.id, "custom", { value: customValue.trim() });
      setShowCustom(false);
      setCustomValue("");
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="relative overflow-hidden rounded-xl border border-border bg-card card-hover"
    >
      {/* Left accent bar */}
      <div className={`absolute left-0 top-0 bottom-0 w-[3px] ${accentColors[card.type] || "bg-muted"}`} />

      <div className="p-4 pl-5">
        {/* Header */}
        <div className="flex items-start gap-2 mb-2">
          <span className="text-lg">{meta.emoji}</span>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-foreground text-sm leading-tight">{card.title}</h3>
          </div>
          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-secondary text-muted-foreground uppercase tracking-wider">
            {meta.label}
          </span>
        </div>

        {/* Body */}
        <p className="text-sm text-foreground/80 mb-2 leading-relaxed">{card.body}</p>

        {/* Agent's reasoning — shows thinking */}
        <div className="text-xs text-muted-foreground mb-3 bg-secondary/30 rounded-lg p-2">
          <span className="font-medium text-foreground/60">Why:</span>{" "}
          <span className="italic">{card.reasoning}</span>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2">
          {card.actions.map((action) => (
            <Button
              key={action.id}
              variant={action.id === "dismiss" || action.id === "skip" ? "ghost" : "secondary"}
              size="sm"
              className={
                action.id === "dismiss" || action.id === "skip"
                  ? "text-muted-foreground text-xs h-7"
                  : "text-xs h-7 hover:bg-primary/10 hover:text-primary"
              }
              onClick={() => onAction(card.id, action.id)}
            >
              {action.label}
            </Button>
          ))}
          {isLearning && !showCustom && (
            <Button
              variant="outline"
              size="sm"
              className="text-xs h-7 border-dashed"
              onClick={() => setShowCustom(true)}
            >
              Other...
            </Button>
          )}
        </div>

        {/* Custom input for learning cards */}
        {isLearning && showCustom && (
          <div className="flex gap-2 mt-3">
            <Input
              placeholder="Type your own answer..."
              value={customValue}
              onChange={(e) => setCustomValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCustomSubmit()}
              className="bg-secondary/50 text-sm h-8"
              autoFocus
            />
            <Button size="sm" className="h-8 text-xs bg-primary text-primary-foreground" onClick={handleCustomSubmit}>
              Send
            </Button>
          </div>
        )}
      </div>
    </motion.div>
  );
}

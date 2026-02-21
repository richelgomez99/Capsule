import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

interface ChatMessage {
  role: "user" | "agent";
  content: string;
  sources?: number;
}

const suggestions = [
  "Summarize my week",
  "What have I been researching?",
  "Any recipes I haven't tried?",
  "What does Capsule know about me?",
];

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim()) return;
    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.chat(text);
      setMessages((prev) => [...prev, {
        role: "agent",
        content: res.response || res.message || "I'm thinking about that...",
        sources: res.sources_count,
      }]);
    } catch {
      setMessages((prev) => [...prev, {
        role: "agent",
        content: "I can't reach my backend right now, but I'm still here. Try again when the API is running!",
      }]);
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] lg:h-[calc(100vh-3rem)] pb-16 lg:pb-0">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto scrollbar-thin space-y-4 py-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-6">
            <div className="text-center">
              <span className="text-4xl">🧠</span>
              <h2 className="text-lg font-semibold text-foreground mt-3">Ask your second brain</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Chat with Capsule about everything it's captured and learned.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 max-w-md">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="px-3 py-2 rounded-lg bg-secondary text-sm text-foreground/80 hover:bg-primary/10 hover:text-primary transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-card border border-border text-foreground"
              }`}
            >
              <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              {msg.sources && (
                <span className="inline-block mt-2 text-[10px] px-2 py-0.5 rounded-full bg-secondary text-muted-foreground">
                  Based on {msg.sources} captures
                </span>
              )}
            </div>
          </motion.div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-card border border-border rounded-xl px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 flex gap-2 pt-3 border-t border-border">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send(input)}
          placeholder="Ask your second brain..."
          className="flex-1 bg-card border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <Button
          onClick={() => send(input)}
          disabled={!input.trim() || loading}
          size="icon"
          className="bg-primary text-primary-foreground rounded-xl h-[46px] w-[46px]"
        >
          <Send size={18} />
        </Button>
      </div>
    </div>
  );
}

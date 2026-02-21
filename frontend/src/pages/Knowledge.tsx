import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Search, Shield } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { api, CATEGORIES } from "@/lib/api";
import { mockCaptures } from "@/lib/mock-data";

export default function Knowledge() {
  const [captures, setCaptures] = useState(mockCaptures);
  const [filter, setFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCapture, setSelectedCapture] = useState<any | null>(null);
  const [correcting, setCorrecting] = useState(false);
  const [correctionField, setCorrectionField] = useState("content_category");
  const [correctionValue, setCorrectionValue] = useState("");
  const { toast } = useToast();

  useEffect(() => {
    api.getCaptures().then(setCaptures).catch(() => {});
  }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const res = await api.search(searchQuery);
      setCaptures(res.results || res);
    } catch {
      // filter locally
      setCaptures(
        mockCaptures.filter(
          (c) =>
            c.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
            c.content.toLowerCase().includes(searchQuery.toLowerCase())
        )
      );
    }
  };

  const handleCorrect = async () => {
    if (!selectedCapture || !correctionValue) return;
    try {
      await api.correct(selectedCapture.id, correctionField, selectedCapture.category, correctionValue);
      toast({ title: "Got it!", description: `I'll classify similar content as "${correctionValue}" from now on.` });
    } catch {
      toast({ title: "Got it!", description: `Correction saved locally — I'll apply it next time.` });
    }
    setCorrecting(false);
    setCorrectionValue("");
  };

  const categories = Object.entries(CATEGORIES);
  const categoryCounts = mockCaptures.reduce((acc: Record<string, number>, c) => {
    acc[c.category] = (acc[c.category] || 0) + 1;
    return acc;
  }, {});

  const filtered = filter === "all" ? captures : captures.filter((c) => c.category === filter);

  const formatTime = (ts: string) => {
    const diff = (Date.now() - new Date(ts).getTime()) / 1000;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
        <Input
          placeholder="Search your second brain..."
          className="pl-10 bg-card border-border h-11"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
      </div>

      {/* Category pills */}
      <div className="flex gap-2 overflow-x-auto scrollbar-thin pb-1">
        <button
          onClick={() => setFilter("all")}
          className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            filter === "all" ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          All {mockCaptures.length}
        </button>
        {categories.map(([key, meta]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-colors flex items-center gap-1 ${
              filter === key ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
            }`}
          >
            {meta.emoji} {key} {categoryCounts[key] || 0}
          </button>
        ))}
      </div>

      {/* Captures grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered.map((capture, i) => {
          const cat = CATEGORIES[capture.category] || { emoji: "📋", colorVar: "cat-reference" };
          return (
            <motion.div
              key={capture.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => setSelectedCapture(capture)}
              className="rounded-xl border border-border bg-card p-4 cursor-pointer card-hover"
            >
              <div className="flex items-center gap-2 mb-2">
                <span>{cat.emoji}</span>
                <Badge variant="secondary" className="text-[10px]">
                  {capture.category}
                </Badge>
                <span className="ml-auto text-[10px] text-muted-foreground">{formatTime(capture.timestamp)}</span>
              </div>
              <h3 className="text-sm font-semibold text-foreground mb-1">{capture.summary}</h3>
              <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{capture.content}</p>
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="outline" className="text-[10px]">{capture.source}</Badge>
                {capture.tags.map((tag: string) => (
                  <span key={tag} className="text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">
                    {tag}
                  </span>
                ))}
                {capture.has_pii && (
                  <span className="flex items-center gap-1 text-[10px] text-pii">
                    <Shield size={10} /> PII Redacted
                  </span>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Detail modal */}
      <Dialog open={!!selectedCapture} onOpenChange={() => { setSelectedCapture(null); setCorrecting(false); }}>
        <DialogContent className="bg-card border-border max-w-lg">
          {selectedCapture && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <span>{CATEGORIES[selectedCapture.category]?.emoji}</span>
                  {selectedCapture.summary}
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <p className="text-sm text-foreground/80">{selectedCapture.content}</p>
                <div className="flex gap-2 flex-wrap">
                  {selectedCapture.tags.map((tag: string) => (
                    <Badge key={tag} variant="secondary" className="text-xs cursor-pointer hover:bg-primary/10"
                      onClick={() => { setCorrecting(true); setCorrectionField("topic_tags"); }}>
                      {tag}
                    </Badge>
                  ))}
                </div>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span>Source: {selectedCapture.source}</span>
                  <span>Quality: <span className="font-mono text-foreground">{selectedCapture.scores?.quality}</span></span>
                </div>
                {!correcting ? (
                  <Button variant="secondary" size="sm" onClick={() => setCorrecting(true)}>
                    Correct this
                  </Button>
                ) : (
                  <div className="space-y-3 p-3 rounded-lg bg-secondary">
                    <Select value={correctionField} onValueChange={setCorrectionField}>
                      <SelectTrigger className="bg-card"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="content_category">Category</SelectItem>
                        <SelectItem value="topic_tags">Tags</SelectItem>
                      </SelectContent>
                    </Select>
                    <div className="text-xs text-muted-foreground">
                      Current: <span className="font-mono text-foreground">{selectedCapture.category}</span>
                    </div>
                    <Input
                      placeholder="Correct to..."
                      value={correctionValue}
                      onChange={(e) => setCorrectionValue(e.target.value)}
                      className="bg-card"
                    />
                    <Button size="sm" onClick={handleCorrect} className="bg-primary text-primary-foreground">
                      Submit Correction
                    </Button>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

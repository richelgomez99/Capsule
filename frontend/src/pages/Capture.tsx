import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, Link, History, CheckCircle, AlertTriangle, Image, Clipboard, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";

interface CaptureResult {
  id: string;
  type: string;
  message: string;
  has_pii?: boolean;
}

export default function Capture() {
  const [results, setResults] = useState<CaptureResult[]>([]);
  const [uploading, setUploading] = useState(false);
  const [textContent, setTextContent] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [historyJson, setHistoryJson] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const addResult = useCallback((result: CaptureResult) => {
    setResults((prev) => [result, ...prev].slice(0, 20));
  }, []);

  const handleScreenshotUpload = useCallback(async (files: File[]) => {
    setUploading(true);
    for (const file of files) {
      try {
        const res = await api.uploadScreenshot(file);
        addResult({ id: res.id, type: "screenshot", message: res.message, has_pii: res.has_pii });
        toast({ title: "Screenshot captured! 📸", description: res.message });
      } catch (err) {
        toast({ title: "Upload failed", description: `Could not upload ${file.name}`, variant: "destructive" });
      }
    }
    setUploading(false);
  }, [addResult, toast]);

  // Global paste handler for screenshots
  useEffect(() => {
    const handlePaste = async (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;

      for (const item of Array.from(items)) {
        if (item.type.startsWith("image/")) {
          e.preventDefault();
          const file = item.getAsFile();
          if (file) {
            await handleScreenshotUpload([file]);
          }
          return;
        }
      }
    };

    window.addEventListener("paste", handlePaste);
    return () => window.removeEventListener("paste", handlePaste);
  }, [handleScreenshotUpload]);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const files = Array.from(e.dataTransfer.files).filter((f) => f.type.startsWith("image/"));
    if (files.length > 0) {
      await handleScreenshotUpload(files);
    }
  }, [handleScreenshotUpload]);

  const handleTextSubmit = async () => {
    if (!textContent.trim()) return;
    setUploading(true);
    try {
      const res = await api.submitText(textContent);
      addResult({ id: res.id, type: "text", message: res.message, has_pii: res.has_pii });
      toast({ title: "Text captured! 📋", description: res.message });
      setTextContent("");
    } catch {
      toast({ title: "Capture failed", description: "Could not save text content.", variant: "destructive" });
    }
    setUploading(false);
  };

  const handleUrlSubmit = async () => {
    if (!urlInput.trim()) return;
    setUploading(true);
    try {
      const res = await api.submitUrl(urlInput);
      addResult({ id: res.id, type: "url", message: res.message, has_pii: res.has_pii });
      toast({ title: "URL captured! 🔗", description: res.message });
      setUrlInput("");
    } catch {
      toast({ title: "Capture failed", description: "Could not fetch URL.", variant: "destructive" });
    }
    setUploading(false);
  };

  const handleHistoryImport = async () => {
    if (!historyJson.trim()) return;
    setUploading(true);
    try {
      const entries = JSON.parse(historyJson);
      const data = Array.isArray(entries) ? entries : [entries];
      const res = await api.importHistory(data);
      addResult({ id: "batch", type: "history", message: res.message });
      toast({ title: "History imported! 📚", description: res.message });
      setHistoryJson("");
    } catch (err) {
      toast({ title: "Import failed", description: "Invalid JSON format. Expected an array of {url, title, visit_time} objects.", variant: "destructive" });
    }
    setUploading(false);
  };

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <h1 className="text-2xl font-bold text-foreground">Capture</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Feed your second brain — upload screenshots, paste text, save URLs, or import browsing history.
        </p>
      </motion.div>

      <Tabs defaultValue="screenshot" className="space-y-4">
        <TabsList className="grid grid-cols-4 w-full">
          <TabsTrigger value="screenshot" className="flex items-center gap-1.5 text-xs">
            <Image size={14} /> Screenshots
          </TabsTrigger>
          <TabsTrigger value="text" className="flex items-center gap-1.5 text-xs">
            <Clipboard size={14} /> Text
          </TabsTrigger>
          <TabsTrigger value="url" className="flex items-center gap-1.5 text-xs">
            <Link size={14} /> URL
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-1.5 text-xs">
            <History size={14} /> History
          </TabsTrigger>
        </TabsList>

        {/* ── Screenshot Upload ── */}
        <TabsContent value="screenshot">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`relative flex flex-col items-center justify-center gap-4 p-12 rounded-xl border-2 border-dashed cursor-pointer transition-all ${
              dragActive
                ? "border-primary bg-primary/5 scale-[1.01]"
                : "border-border bg-card hover:border-primary/50 hover:bg-primary/[0.02]"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              multiple
              className="hidden"
              onChange={(e) => {
                const files = Array.from(e.target.files || []);
                if (files.length) handleScreenshotUpload(files);
              }}
            />
            <Upload size={36} className={dragActive ? "text-primary" : "text-muted-foreground"} />
            <div className="text-center">
              <p className="text-sm font-medium text-foreground">
                {dragActive ? "Drop screenshots here" : "Drag & drop screenshots"}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                or click to browse · PNG, JPG, WebP, GIF · max 10 MB
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                💡 Tip: Paste screenshots directly with <kbd className="px-1 py-0.5 rounded bg-secondary text-foreground text-[10px]">Ctrl+V</kbd>
              </p>
            </div>
            {uploading && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/50 rounded-xl">
                <div className="flex items-center gap-2 text-sm text-primary">
                  <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Processing...
                </div>
              </div>
            )}
          </div>
        </TabsContent>

        {/* ── Text / Clipboard ── */}
        <TabsContent value="text">
          <div className="space-y-3">
            <textarea
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              placeholder="Paste clipboard content, code snippets, notes, or any text..."
              className="w-full h-48 bg-card border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {textContent.length > 0 ? `${textContent.length} characters` : "Paste or type anything"}
              </span>
              <Button
                onClick={handleTextSubmit}
                disabled={!textContent.trim() || uploading}
                className="bg-primary text-primary-foreground"
              >
                <FileText size={16} className="mr-2" />
                Capture Text
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* ── URL Capture ── */}
        <TabsContent value="url">
          <div className="space-y-3">
            <div className="flex gap-2">
              <Input
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleUrlSubmit()}
                placeholder="https://example.com/article-you-want-to-remember"
                className="bg-card border-border h-11"
              />
              <Button
                onClick={handleUrlSubmit}
                disabled={!urlInput.trim() || uploading}
                className="bg-primary text-primary-foreground shrink-0"
              >
                <Link size={16} className="mr-2" />
                Capture
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Capsule will fetch the page, extract the title and content, and save it to your knowledge base.
            </p>
          </div>
        </TabsContent>

        {/* ── Browsing History Import ── */}
        <TabsContent value="history">
          <div className="space-y-3">
            <textarea
              value={historyJson}
              onChange={(e) => setHistoryJson(e.target.value)}
              placeholder={`Paste browsing history as JSON:\n[\n  {"url": "https://...", "title": "Page Title", "visit_time": "2026-01-15T10:30:00"},\n  ...\n]`}
              className="w-full h-48 bg-card border border-border rounded-xl px-4 py-3 text-sm font-mono text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                JSON array of objects with url, title, and visit_time fields
              </span>
              <Button
                onClick={handleHistoryImport}
                disabled={!historyJson.trim() || uploading}
                className="bg-primary text-primary-foreground"
              >
                <History size={16} className="mr-2" />
                Import History
              </Button>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* ── Recent Captures ── */}
      <AnimatePresence>
        {results.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-3"
          >
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Recent Captures
            </h2>
            {results.map((result, i) => (
              <motion.div
                key={`${result.id}-${i}`}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-start gap-3 p-3 rounded-lg bg-card border border-border"
              >
                <span className="text-lg shrink-0">
                  {result.type === "screenshot" ? "📸" : result.type === "url" ? "🔗" : result.type === "history" ? "📚" : "📋"}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground">{result.message}</p>
                  <div className="flex gap-2 mt-1">
                    <Badge variant="secondary" className="text-[10px]">{result.type}</Badge>
                    {result.has_pii && (
                      <Badge variant="outline" className="text-[10px] text-yellow-500 border-yellow-500/30">
                        <AlertTriangle size={10} className="mr-1" /> PII Detected
                      </Badge>
                    )}
                  </div>
                </div>
                <CheckCircle size={16} className="text-green-500 shrink-0 mt-1" />
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Empty state prompt ── */}
      {results.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-center py-8"
        >
          <p className="text-sm text-muted-foreground">
            Start capturing to build your knowledge base. After capturing, go to{" "}
            <span className="text-primary font-medium">Feed</span> and click{" "}
            <span className="text-primary font-medium">"Process Today's Saves"</span> to classify everything.
          </p>
        </motion.div>
      )}
    </div>
  );
}

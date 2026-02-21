import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Activity, BookOpen, Brain, MessageSquare, Trophy, Settings, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", icon: Activity, label: "Feed" },
  { to: "/knowledge", icon: BookOpen, label: "Knowledge" },
  { to: "/chat", icon: MessageSquare, label: "Chat" },
  { to: "/about-me", icon: Brain, label: "About Me" },
  { to: "/judge", icon: Trophy, label: "Judge" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Mobile header */}
      <header className="lg:hidden flex items-center justify-between px-4 h-14 border-b border-border bg-card">
        <div className="flex items-center gap-2">
          <span className="text-primary text-lg font-semibold">◉</span>
          <span className="font-semibold text-foreground">Capsule</span>
        </div>
        <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-muted-foreground">
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-40 bg-background/80 backdrop-blur-sm" onClick={() => setSidebarOpen(false)}>
          <nav className="w-60 h-full bg-card border-r border-border p-4 flex flex-col gap-1" onClick={(e) => e.stopPropagation()}>
            <SidebarContent currentPath={location.pathname} onNavigate={() => setSidebarOpen(false)} />
          </nav>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-[240px] shrink-0 border-r border-border bg-card flex-col">
        <div className="p-5 flex items-center gap-2.5">
          <span className="text-primary text-xl">◉</span>
          <span className="font-semibold text-foreground text-lg">Capsule</span>
          <span className="ml-auto flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="w-2 h-2 rounded-full bg-score-green pulse-green" />
            Running
          </span>
        </div>
        <nav className="flex-1 px-3 flex flex-col gap-0.5">
          <SidebarContent currentPath={location.pathname} />
        </nav>
        <div className="p-3 border-t border-border">
          <button className="flex items-center gap-2 px-3 py-2 w-full rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors">
            <Settings size={16} />
            Settings
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 overflow-auto">
        <div className="max-w-[1200px] mx-auto p-4 lg:p-6">
          {children}
        </div>
      </main>

      {/* Mobile bottom tab bar */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-card border-t border-border flex z-30">
        {navItems.map((item) => {
          const active = item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to);
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={cn(
                "flex-1 flex flex-col items-center gap-0.5 py-2 text-xs transition-colors",
                active ? "text-primary" : "text-muted-foreground"
              )}
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}

function SidebarContent({ currentPath, onNavigate }: { currentPath: string; onNavigate?: () => void }) {
  return (
    <>
      {navItems.map((item) => {
        const active = item.to === "/" ? currentPath === "/" : currentPath.startsWith(item.to);
        return (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all",
              active
                ? "bg-primary/10 text-primary font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary"
            )}
          >
            <item.icon size={18} />
            {item.label}
          </NavLink>
        );
      })}
    </>
  );
}

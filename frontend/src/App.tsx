import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Feed from "@/pages/Feed";
import Knowledge from "@/pages/Knowledge";
import Chat from "@/pages/Chat";
import AboutMe from "@/pages/AboutMe";
import JudgePanel from "@/pages/JudgePanel";
import NotFound from "@/pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Feed />} />
            <Route path="/knowledge" element={<Knowledge />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/about-me" element={<AboutMe />} />
            <Route path="/judge" element={<JudgePanel />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;

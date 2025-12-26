import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChatInterface } from '@/components/ChatInterface';
import { Sidebar } from '@/components/Sidebar';
import { SidebarProvider } from '@/components/ui/sidebar';
import { getUserInfo, isAuthenticated, removeToken } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { v4 as uuidv4 } from 'uuid';

const Index = () => {
  const [currentChatId, setCurrentChatId] = useState<string>(() => uuidv4());
  const [user, setUser] = useState<{ sub: string; role: string } | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate('/login');
      return;
    }
    setUser(getUserInfo());
  }, [navigate]);
  // On every mount (reload), always start with a new chat session
  useEffect(() => {
    setCurrentChatId(uuidv4());
  }, []);

  const handleLogout = () => {
    removeToken();
    navigate('/login');
  };

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full bg-white">
        {/* Sidebar and ChatInterface side by side */}
        <Sidebar currentChatId={currentChatId} onChatSelect={setCurrentChatId} />
        <main className="flex-1 flex flex-col" style={{background: '#fff', minHeight: '100vh', boxShadow: '0 0 0 1px #e5e7eb'}}>
          <ChatInterface chatId={currentChatId} />
        </main>
      </div>
    </SidebarProvider>
  );
};

export default Index;

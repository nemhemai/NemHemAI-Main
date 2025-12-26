
import { useState, useEffect, useCallback } from 'react';
import { Plus, MessageSquare, Settings, Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useSidebar } from '@/components/ui/sidebar';
import { listChats, createChat } from '@/lib/chatHistory';
import { getUserInfo } from '@/lib/api';

interface Chat {
  id: string;
  title: string;
  timestamp: Date;
}

interface SidebarProps {
  currentChatId: string;
  onChatSelect: (chatId: string) => void;
}

export const Sidebar = ({ currentChatId, onChatSelect }: SidebarProps) => {
  const { open, setOpen } = useSidebar();
  const [chats, setChats] = useState<Chat[]>([]);
  const user = getUserInfo();

  // Load chat sessions for the user
  const loadChats = useCallback(async () => {
    if (!user) return;
    const allChats = await listChats();
    // Filter chats for this user
    const userChats = allChats
      .filter((c) => c.userId === user.sub + '_' + c.sessionId)
      .map((c) => {
        return {
          id: c.sessionId,
          title: c.lastMessage?.content?.slice(0, 20) || 'Chat',
          timestamp: new Date(c.lastMessage?.timestamp || Date.now()),
        };
      })
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
    setChats(userChats);
  }, [user]);

  useEffect(() => {
    loadChats();
    // Optionally, reload when sidebar is opened
  }, [loadChats, open]);

  const createNewChat = async () => {
    const newChatId = Date.now().toString();
    if (user) {
      // Compose userId as before
      const userId = user.sub + '_' + newChatId;
      await createChat(userId, newChatId);
      await loadChats(); // Refresh sidebar
      onChatSelect(newChatId);
    }
    // The chat will appear after the first message is sent
  };

  return (
    <div className={`${!open ? 'w-16' : 'w-80'} transition-all duration-300 bg-white border-r border-gray-100 shadow-lg flex flex-col h-screen`}>
      {/* Header */}
      <div className="p-4">
        <div className="flex items-center justify-between">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setOpen(!open)}
            className="text-slate-400 hover:text-white hover:bg-slate-700/50 transition-all duration-200"
          >
            {!open ? <Menu className="h-5 w-5" /> : <X className="h-5 w-5" />}
          </Button>
          {open && (
            <Button
              onClick={createNewChat}
              className="bg-gradient-to-r from-[#181C5A] to-[#B983FD] text-white font-bold rounded-[12px] px-4 h-8 text-sm shadow-md hover:brightness-110 transition-all duration-200 flex items-center"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Chat
            </Button>
          )}
        </div>
      </div>

      {/* Chat List */}
      <ScrollArea className="flex-1 px-2">
        {open && (
          <div className="space-y-2 py-4">
            {chats.map((chat) => (
              <button
                key={chat.id}
                onClick={() => onChatSelect(chat.id)}
                className={`w-full text-left p-4 rounded-xl transition-all duration-200 ${
                  currentChatId === chat.id
                    ? 'bg-[#F3E8FF] text-black shadow border-2 border-[#A259FF]'
                    : 'hover:bg-gray-50 text-[#181C5A]'
                }`}
              >
                <div className="flex items-center gap-3">
                  <MessageSquare className="h-4 w-4 text-slate-400" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-black truncate">
                      {chat.title}
                    </p>
                    <p className="text-xs text-slate-400">
                      {chat.timestamp.toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Settings */}
      <div className="p-4 border-t border-slate-700/50 mt-auto">
        <Button
          variant="ghost"
          className={`${!open ? 'w-8 h-8 p-0' : 'w-full justify-start'} text-slate-400 hover:text-white hover:bg-slate-700/50 transition-all duration-200`}
        >
          <Settings className="h-4 w-4" />
          {open && <span className="ml-2">Settings</span>}
        </Button>
      </div>
    </div>
  );
};

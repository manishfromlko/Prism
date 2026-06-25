'use client'

import { useState } from 'react'
import { Sidebar } from './sidebar'
import { Header } from './header'
import { ChatPanel } from '@/components/chatbot/ChatPanel'
import { Toaster } from '@/components/ui/toaster'

export function AppShell({ children }: { children: React.ReactNode }) {
  const [chatOpen, setChatOpen] = useState(false)

  return (
    <div className="flex h-screen">
      <Sidebar onChatToggle={() => setChatOpen((o) => !o)} chatOpen={chatOpen} />
      <div className="flex-1 flex overflow-hidden">
        <div className="flex flex-col flex-1 overflow-hidden">
          <Header onChatToggle={() => setChatOpen((o) => !o)} chatOpen={chatOpen} />
          <main className="flex-1 overflow-auto p-6">{children}</main>
        </div>
        <ChatPanel isOpen={chatOpen} onClose={() => setChatOpen(false)} />
      </div>
      <Toaster />
    </div>
  )
}

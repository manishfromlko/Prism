'use client'

import { useEffect, useRef, useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { MessageSquare, X, Trash2, Maximize2, Minimize2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ChatMessage, ChatMessageData } from './ChatMessage'
import { ChatInput } from './ChatInput'

const WELCOME: ChatMessageData = {
  role: 'assistant',
  content:
    'Hi! I can help with:\n• Platform docs & how-to guides\n• Finding code artifacts & notebooks\n• Discovering people & expertise\n\nWhat would you like to know?',
}

interface ChatPanelProps {
  isOpen: boolean
  onClose: () => void
}

export function ChatPanel({ isOpen, onClose }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessageData[]>([WELCOME])
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Collapse back to default width when closed
  useEffect(() => {
    if (!isOpen) setExpanded(false)
  }, [isOpen])

  const handleSend = async (query: string) => {
    const userMsg: ChatMessageData = { role: 'user', content: query }
    const loadingMsg: ChatMessageData = { role: 'assistant', content: '', isLoading: true }

    setMessages((prev) => [...prev, userMsg, loadingMsg])
    setLoading(true)

    const history = messages
      .filter((m) => !m.isLoading && m.content !== WELCOME.content)
      .map((m) => ({ role: m.role, content: m.content }))

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, history }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }

      const data = await res.json()
      const assistantMsg: ChatMessageData = {
        role: 'assistant',
        content: data.answer,
        intent: data.intent,
        confidence: data.confidence,
        artifacts: data.artifacts,
        users: data.users,
        sources: data.sources,
      }

      setMessages((prev) => [...prev.slice(0, -1), assistantMsg])
    } catch (err: any) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: `Sorry, something went wrong: ${err.message}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => setMessages([WELCOME])

  return (
    <div
      className={cn(
        'flex flex-col border-l bg-background transition-all duration-300 overflow-hidden shrink-0',
        !isOpen && 'w-0',
        isOpen && !expanded && 'w-80',
        isOpen && expanded && 'w-[600px]',
      )}
    >
      {isOpen && (
        <>
          {/* Header */}
          <div className="flex h-12 items-center justify-between border-b px-3 shrink-0">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-primary" />
              <span className="text-sm font-semibold">Assistant</span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={handleClear}
                title="Clear conversation"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={() => setExpanded((e) => !e)}
                title={expanded ? 'Collapse panel' : 'Expand panel'}
              >
                {expanded
                  ? <Minimize2 className="h-3.5 w-3.5" />
                  : <Maximize2 className="h-3.5 w-3.5" />
                }
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={onClose}
                title="Close"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          {/* Messages */}
          <ScrollArea className="flex-1 px-3 py-4">
            <div className="space-y-4">
              {messages.map((msg, i) => (
                <ChatMessage key={i} message={msg} />
              ))}
              <div ref={bottomRef} />
            </div>
          </ScrollArea>

          {/* Input */}
          <ChatInput onSend={handleSend} disabled={loading} />
        </>
      )}
    </div>
  )
}

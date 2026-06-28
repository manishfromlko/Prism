'use client'

import { useEffect, useRef, useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { History, Maximize2, MessageSquare, Minimize2, Plus, Trash2, X } from 'lucide-react'
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

interface ConversationSummary {
  session_id: string
  title: string
  updated_at?: string | null
  message_count: number
}

interface ConversationHistory {
  session_id: string
  title: string
  messages: Array<{ role: 'user' | 'assistant'; content: string }>
}

export function ChatPanel({ isOpen, onClose }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessageData[]>([WELCOME])
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const sessionIdRef = useRef<string>(crypto.randomUUID())
  const hydratedRef = useRef(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Collapse back to default width when closed
  useEffect(() => {
    if (!isOpen) setExpanded(false)
  }, [isOpen])

  const loadConversations = async () => {
    try {
      const res = await fetch('/api/chat/conversations', { cache: 'no-store' })
      if (!res.ok) return []
      const data = await res.json()
      const rows = data.data ?? []
      setConversations(rows)
      return rows as ConversationSummary[]
    } catch {
      return []
    }
  }

  const loadConversation = async (sessionId: string) => {
    const res = await fetch(`/api/chat/conversations/${encodeURIComponent(sessionId)}`, {
      cache: 'no-store',
    })
    if (!res.ok) return
    const data: ConversationHistory = await res.json()
    sessionIdRef.current = data.session_id
    setMessages([
      WELCOME,
      ...data.messages.map((message) => ({
        role: message.role,
        content: message.content,
      })),
    ])
  }

  useEffect(() => {
    if (!isOpen || hydratedRef.current) return
    hydratedRef.current = true
    loadConversations().then((rows) => {
      if (rows.length > 0) {
        loadConversation(rows[0].session_id)
      }
    })
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
        body: JSON.stringify({ query, history, session_id: sessionIdRef.current }),
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
        exact_match: data.exact_match ?? false,
        artifacts: data.artifacts,
        users: data.users,
        sources: data.sources,
        agent_mode: data.agent_mode,
        agent_steps: data.agent_steps,
      }

      setMessages((prev) => [...prev.slice(0, -1), assistantMsg])
      loadConversations()
    } catch (err: any) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: `Sorry, something went wrong: ${err.message}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    sessionIdRef.current = crypto.randomUUID()
    setMessages([WELCOME])
  }

  const handleDeleteCurrent = async () => {
    const currentSessionId = sessionIdRef.current
    try {
      await fetch(`/api/chat/conversations/${encodeURIComponent(currentSessionId)}`, {
        method: 'DELETE',
      })
    } catch {
      // Non-fatal: starting a fresh local conversation is still useful.
    }
    handleClear()
    loadConversations()
  }

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
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    title="Saved conversations"
                  >
                    <History className="h-3.5 w-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-64">
                  <DropdownMenuLabel>Saved conversations</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleClear}>
                    <Plus className="mr-2 h-3.5 w-3.5" />
                    New conversation
                  </DropdownMenuItem>
                  {conversations.length > 0 && <DropdownMenuSeparator />}
                  {conversations.map((conversation) => (
                    <DropdownMenuItem
                      key={conversation.session_id}
                      onClick={() => loadConversation(conversation.session_id)}
                      className="flex-col items-start gap-0.5"
                    >
                      <span className="w-full truncate text-sm">{conversation.title}</span>
                      <span className="text-xs text-muted-foreground">
                        {conversation.message_count} messages
                      </span>
                    </DropdownMenuItem>
                  ))}
                  {conversations.length === 0 && (
                    <DropdownMenuItem disabled>No saved conversations</DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={handleDeleteCurrent}
                title="Delete current conversation"
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

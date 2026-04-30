'use client'

import { cn } from '@/lib/utils'

export interface ArtifactResult {
  title: string
  reason: string
  owner: string
}

export interface UserResult {
  name: string
  reason: string
  skills: string[]
}

export interface SourceResult {
  file: string
  doc_id: string
}

export interface ChatMessageData {
  role: 'user' | 'assistant'
  content: string
  intent?: string
  confidence?: number
  artifacts?: ArtifactResult[]
  users?: UserResult[]
  sources?: SourceResult[]
  isLoading?: boolean
}

const INTENT_COLORS: Record<string, string> = {
  DOC_QA: 'bg-blue-100 text-blue-800',
  ARTIFACT_SEARCH: 'bg-purple-100 text-purple-800',
  USER_SEARCH: 'bg-green-100 text-green-800',
  HYBRID: 'bg-orange-100 text-orange-800',
}

function LoadingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
      <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
      <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
    </div>
  )
}

export function ChatMessage({ message }: { message: ChatMessageData }) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex flex-col gap-1', isUser ? 'items-end' : 'items-start')}>
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap',
          isUser
            ? 'bg-primary text-primary-foreground rounded-br-sm'
            : 'bg-muted text-foreground rounded-bl-sm'
        )}
      >
        {message.isLoading ? <LoadingDots /> : message.content}
      </div>

      {/* Intent badge */}
      {!isUser && message.intent && (
        <div className="flex items-center gap-2 px-1">
          <span
            className={cn(
              'text-[10px] font-medium px-1.5 py-0.5 rounded-full',
              INTENT_COLORS[message.intent] ?? 'bg-gray-100 text-gray-700'
            )}
          >
            {message.intent}
          </span>
          {message.confidence !== undefined && (
            <span className="text-[10px] text-muted-foreground">
              {Math.round(message.confidence * 100)}% confidence
            </span>
          )}
        </div>
      )}

      {/* Artifacts */}
      {!isUser && message.artifacts && message.artifacts.length > 0 && (
        <div className="w-full max-w-[85%] rounded-xl border bg-card p-3 text-xs space-y-2">
          <p className="font-semibold text-muted-foreground uppercase tracking-wide text-[10px]">
            Artifacts
          </p>
          {message.artifacts.map((a, i) => (
            <div key={i} className="space-y-0.5">
              <p className="font-medium truncate">{a.title}</p>
              <p className="text-muted-foreground">Owner: {a.owner}</p>
            </div>
          ))}
        </div>
      )}

      {/* Users */}
      {!isUser && message.users && message.users.length > 0 && (
        <div className="w-full max-w-[85%] rounded-xl border bg-card p-3 text-xs space-y-2">
          <p className="font-semibold text-muted-foreground uppercase tracking-wide text-[10px]">
            People
          </p>
          {message.users.map((u, i) => (
            <div key={i}>
              <p className="font-medium">{u.name}</p>
            </div>
          ))}
        </div>
      )}

      {/* Sources */}
      {!isUser && message.sources && message.sources.length > 0 && (
        <div className="w-full max-w-[85%] px-1">
          <p className="text-[10px] text-muted-foreground">
            Sources: {message.sources.map((s) => s.file).join(', ')}
          </p>
        </div>
      )}
    </div>
  )
}

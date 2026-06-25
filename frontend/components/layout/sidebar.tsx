'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Home,
  Search,
  FolderOpen,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  Users,
  MessageSquare,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Search', href: '/search', icon: Search },
  { name: 'User Profiles', href: '/user-profiles', icon: Users },
  { name: 'Workspaces', href: '/workspaces', icon: FolderOpen },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Settings', href: '/settings', icon: Settings },
]

interface SidebarProps {
  className?: string
  onChatToggle?: () => void
  chatOpen?: boolean
}

export function Sidebar({ className, onChatToggle, chatOpen }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()

  return (
    <div
      className={cn(
        'flex flex-col border-r bg-card transition-all duration-300',
        collapsed ? 'w-16' : 'w-64',
        className
      )}
    >
      {/* Header */}
      <div className="flex h-16 items-center justify-between px-4">
        {!collapsed && <h2 className="text-lg font-semibold">Workspace</h2>}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCollapsed(!collapsed)}
          className="h-8 w-8 p-0"
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      <Separator />

      {/* Navigation */}
      <ScrollArea className="flex-1 px-3">
        <nav className="space-y-2 py-4">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link key={item.name} href={item.href}>
                <Button
                  variant={isActive ? 'secondary' : 'ghost'}
                  className={cn(
                    'w-full justify-start',
                    collapsed ? 'px-2' : 'px-3',
                    isActive && 'bg-secondary'
                  )}
                >
                  <item.icon className={cn('h-4 w-4', !collapsed && 'mr-3')} />
                  {!collapsed && <span>{item.name}</span>}
                </Button>
              </Link>
            )
          })}
        </nav>
      </ScrollArea>

      <Separator />

      {/* Chat toggle at bottom of sidebar */}
      <div className="p-3">
        <Button
          variant={chatOpen ? 'secondary' : 'ghost'}
          className={cn('w-full justify-start', collapsed ? 'px-2' : 'px-3')}
          onClick={onChatToggle}
          title="Toggle AI Assistant"
        >
          <MessageSquare className={cn('h-4 w-4', !collapsed && 'mr-3')} />
          {!collapsed && <span>AI Assistant</span>}
        </Button>
        {!collapsed && (
          <p className="mt-2 text-[10px] text-muted-foreground px-1">v1.0.0</p>
        )}
      </div>
    </div>
  )
}

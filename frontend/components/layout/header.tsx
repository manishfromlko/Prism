'use client'

import { Bell, MessageSquare, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { SearchBar } from '@/components/search/SearchBar'
import { cn } from '@/lib/utils'

interface HeaderProps {
  onChatToggle?: () => void
  chatOpen?: boolean
}

export function Header({ onChatToggle, chatOpen }: HeaderProps) {
  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-6 gap-4">
      {/* Search Bar */}
      <div className="flex-1 max-w-md">
        <SearchBar placeholder="Search workspaces..." />
      </div>

      {/* Right side actions */}
      <div className="flex items-center space-x-2 ml-auto">
        {/* AI Chat toggle */}
        <Button
          variant={chatOpen ? 'secondary' : 'ghost'}
          size="sm"
          onClick={onChatToggle}
          title="Toggle AI Assistant"
          className={cn('gap-2', chatOpen && 'bg-secondary')}
        >
          <MessageSquare className="h-4 w-4" />
          <span className="hidden sm:inline text-sm">Assistant</span>
        </Button>

        {/* Notifications */}
        <Button variant="ghost" size="sm" className="relative">
          <Bell className="h-4 w-4" />
          <Badge
            variant="destructive"
            className="absolute -right-1 -top-1 h-5 w-5 rounded-full p-0 text-xs"
          >
            3
          </Badge>
        </Button>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-8 w-8 rounded-full">
              <Avatar className="h-8 w-8">
                <AvatarImage src="/avatars/01.png" alt="User" />
                <AvatarFallback>U</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">User</p>
                <p className="text-xs leading-none text-muted-foreground">
                  user@example.com
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <span>Settings</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}

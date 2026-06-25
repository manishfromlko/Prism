'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search, X } from 'lucide-react'

interface SearchBarProps {
  onSearch?: (query: string) => void
  defaultValue?: string
  placeholder?: string
}

export function SearchBar({
  onSearch,
  defaultValue = '',
  placeholder = 'Search across workspaces...',
}: SearchBarProps) {
  const router = useRouter()
  const [query, setQuery] = useState(defaultValue)

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      if (onSearch) {
        onSearch(query)
      } else {
        router.push(`/search?q=${encodeURIComponent(query)}`)
      }
    }
  }

  const handleClear = () => {
    setQuery('')
  }

  return (
    <form onSubmit={handleSearch} className="w-full">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-9 pr-9"
        />
        {query && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </form>
  )
}
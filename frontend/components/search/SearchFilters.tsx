'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { SearchFilters as SearchFiltersType } from '@/types'

interface SearchFiltersProps {
  onFilterChange?: (filters: Partial<SearchFiltersType>) => void
  defaultFilters?: Partial<SearchFiltersType>
}

const FILE_TYPES = ['python', 'notebook', 'markdown', 'yaml', 'json', 'text', 'sql']
const LANGUAGES = ['Python', 'JavaScript', 'SQL', 'Markdown', 'YAML', 'JSON', 'C++', 'Java']

export function SearchFilters({
  onFilterChange,
  defaultFilters = {},
}: SearchFiltersProps) {
  const [expanded, setExpanded] = useState(true)
  const [selectedFileTypes, setSelectedFileTypes] = useState<string[]>(
    defaultFilters.file_types || []
  )
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(
    defaultFilters.languages || []
  )
  const [minScore, setMinScore] = useState<number>(defaultFilters.min_score || 0)

  const handleFileTypeChange = (fileType: string, checked: boolean) => {
    const updated = checked
      ? [...selectedFileTypes, fileType]
      : selectedFileTypes.filter((t) => t !== fileType)
    setSelectedFileTypes(updated)
    onFilterChange?.({
      file_types: updated.length > 0 ? updated : undefined,
    })
  }

  const handleLanguageChange = (language: string, checked: boolean) => {
    const updated = checked
      ? [...selectedLanguages, language]
      : selectedLanguages.filter((l) => l !== language)
    setSelectedLanguages(updated)
    onFilterChange?.({
      languages: updated.length > 0 ? updated : undefined,
    })
  }

  const handleResetFilters = () => {
    setSelectedFileTypes([])
    setSelectedLanguages([])
    setMinScore(0)
    onFilterChange?.({
      file_types: undefined,
      languages: undefined,
      min_score: undefined,
    })
  }

  const activeFilterCount =
    selectedFileTypes.length + selectedLanguages.length + (minScore > 0 ? 1 : 0)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">Filters</CardTitle>
            {activeFilterCount > 0 && (
              <Badge variant="secondary">{activeFilterCount}</Badge>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            className="h-8 w-8 p-0"
          >
            {expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardHeader>

      {expanded && (
        <>
          <Separator />
          <CardContent className="pt-4 space-y-4">
            {/* File Type Filter */}
            <div className="space-y-2">
              <h4 className="font-medium text-sm">File Type</h4>
              <div className="space-y-2">
                {FILE_TYPES.map((fileType) => (
                  <div key={fileType} className="flex items-center space-x-2">
                    <Checkbox
                      id={`filetype-${fileType}`}
                      checked={selectedFileTypes.includes(fileType)}
                      onCheckedChange={(checked) =>
                        handleFileTypeChange(fileType, !!checked)
                      }
                    />
                    <Label
                      htmlFor={`filetype-${fileType}`}
                      className="text-sm font-normal cursor-pointer"
                    >
                      {fileType}
                    </Label>
                  </div>
                ))}
              </div>
            </div>

            <Separator />

            {/* Language Filter */}
            <div className="space-y-2">
              <h4 className="font-medium text-sm">Language</h4>
              <div className="space-y-2">
                {LANGUAGES.map((language) => (
                  <div key={language} className="flex items-center space-x-2">
                    <Checkbox
                      id={`language-${language}`}
                      checked={selectedLanguages.includes(language)}
                      onCheckedChange={(checked) =>
                        handleLanguageChange(language, !!checked)
                      }
                    />
                    <Label
                      htmlFor={`language-${language}`}
                      className="text-sm font-normal cursor-pointer"
                    >
                      {language}
                    </Label>
                  </div>
                ))}
              </div>
            </div>

            <Separator />

            {/* Min Score Filter */}
            <div className="space-y-3">
              <h4 className="font-medium text-sm">Minimum Relevance</h4>
              <div className="space-y-2">
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="10"
                  value={minScore}
                  onChange={(e) => {
                    const value = Number(e.target.value)
                    setMinScore(value)
                    onFilterChange?.({
                      min_score: value > 0 ? value / 100 : undefined,
                    })
                  }}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>0%</span>
                  <span className="font-medium">{minScore}%</span>
                  <span>100%</span>
                </div>
              </div>
            </div>

            {/* Reset Button */}
            {activeFilterCount > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetFilters}
                className="w-full"
              >
                Reset Filters
              </Button>
            )}
          </CardContent>
        </>
      )}
    </Card>
  )
}
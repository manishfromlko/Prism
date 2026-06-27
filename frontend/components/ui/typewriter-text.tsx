'use client'

import { useEffect, useState } from 'react'

type TypewriterTextProps = {
  text: string
  speedMs?: number
  className?: string
}

const DEFAULT_SPEED_MS = 30

export function TypewriterText({ text, speedMs = DEFAULT_SPEED_MS, className }: TypewriterTextProps) {
  const [visibleLength, setVisibleLength] = useState(0)

  useEffect(() => {
    setVisibleLength(0)

    if (!text) {
      return
    }

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setVisibleLength(text.length)
      return
    }

    const interval = window.setInterval(() => {
      setVisibleLength((current) => {
        if (current >= text.length) {
          window.clearInterval(interval)
          return current
        }

        return current + 1
      })
    }, speedMs)

    return () => window.clearInterval(interval)
  }, [speedMs, text])

  const isComplete = visibleLength >= text.length

  return (
    <span className={className}>
      <span aria-hidden="true">{text.slice(0, visibleLength)}</span>
      {!isComplete && <span aria-hidden="true" className="animate-pulse">|</span>}
      <span className="sr-only">{text}</span>
    </span>
  )
}

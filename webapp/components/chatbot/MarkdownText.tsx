'use client'

import { Fragment } from 'react'

/**
 * Renders a subset of markdown inline in a React span:
 *   **bold text**  → <strong>
 *   \n             → <br />
 *
 * No external dependency — covers the patterns the chatbot actually produces.
 */
export function MarkdownText({ text }: { text: string }) {
  // Split on newlines first, then handle **bold** within each line
  const lines = text.split('\n')

  return (
    <>
      {lines.map((line, li) => (
        <Fragment key={li}>
          {li > 0 && <br />}
          {parseBold(line)}
        </Fragment>
      ))}
    </>
  )
}

function parseBold(line: string) {
  const parts = line.split('**')
  return parts.map((part, i) =>
    i % 2 === 1
      ? <strong key={i}>{part}</strong>
      : <Fragment key={i}>{part}</Fragment>
  )
}

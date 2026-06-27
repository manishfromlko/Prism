import { NextResponse } from 'next/server'

const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const response = await fetch(`${PYTHON_API_URL}/chat/conversations`, { cache: 'no-store' })
    const data = await response.json()
    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ detail: 'Conversation history unavailable' }, { status: 503 })
  }
}

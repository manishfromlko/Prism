import { NextRequest, NextResponse } from 'next/server'

const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:8000'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params
    const response = await fetch(
      `${PYTHON_API_URL}/chat/conversations/${encodeURIComponent(id)}`,
      { cache: 'no-store' },
    )
    const data = await response.json()
    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ detail: 'Conversation history unavailable' }, { status: 503 })
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params
    const response = await fetch(
      `${PYTHON_API_URL}/chat/conversations/${encodeURIComponent(id)}`,
      { method: 'DELETE' },
    )
    const data = await response.json()
    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ detail: 'Conversation delete failed' }, { status: 503 })
  }
}

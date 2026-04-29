import { NextRequest, NextResponse } from 'next/server'

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000'

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const query = searchParams.toString()
    const url = `${PYTHON_API}/workspaces${query ? `?${query}` : ''}`

    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) {
      const text = await res.text()
      return NextResponse.json({ error: text }, { status: res.status })
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch (err) {
    console.error('[/api/workspaces] fetch error:', err)
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 })
  }
}

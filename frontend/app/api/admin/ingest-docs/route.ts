import { NextRequest, NextResponse } from 'next/server'

const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const dropExisting = searchParams.get('drop_existing') === 'true'
    const response = await fetch(
      `${PYTHON_API_URL}/admin/ingest-docs?drop_existing=${dropExisting}`,
      { method: 'POST' }
    )
    const data = await response.json()
    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }
    return NextResponse.json(data)
  } catch (error) {
    return NextResponse.json({ detail: 'Doc ingestion request failed' }, { status: 500 })
  }
}

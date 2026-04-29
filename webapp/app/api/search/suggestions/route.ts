import { NextResponse } from 'next/server'

// Search suggestions are not yet implemented in the Python backend.
// Return an empty list so the webapp degrades gracefully.
export async function GET() {
  return NextResponse.json([])
}

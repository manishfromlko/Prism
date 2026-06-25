/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    optimizePackageImports: [
      'lucide-react',
      'recharts',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-scroll-area',
      '@radix-ui/react-toast',
    ],
  },
  // PYTHON_API_URL is a server-side env var used by the /api/* route handlers.
  // It is NOT exposed to the browser. Default: http://localhost:8000
  // Override by setting PYTHON_API_URL in your environment or .env.local
  env: {
    PYTHON_API_URL: process.env.PYTHON_API_URL || 'http://localhost:8000',
  },
}

module.exports = nextConfig

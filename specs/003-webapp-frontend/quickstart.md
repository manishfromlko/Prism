# Webapp Frontend Quickstart Guide

## Prerequisites

- **Node.js 18+**: Required for Next.js 14
- **npm or yarn**: Package manager
- **Git**: Version control
- **Backend API**: Running retrieval API (see main README)

## Local Development Setup

### 1. Install Dependencies

```bash
# Navigate to the webapp directory (create if doesn't exist)
cd webapp

# Install dependencies
npm install
# or
yarn install
```

### 2. Environment Configuration

Create a `.env.local` file in the webapp directory:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Development
NODE_ENV=development
NEXT_PUBLIC_APP_ENV=development

# Optional: Analytics, Monitoring
NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
```

### 3. Start Development Server

```bash
npm run dev
# or
yarn dev
```

The application will be available at `http://localhost:3000`

### 4. Backend API Setup

Ensure the retrieval API is running:

```bash
# In a separate terminal, from project root
cd src/retrieval
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

## Project Structure

```
webapp/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Dashboard page
│   ├── workspace/         # Workspace detail pages
│   └── api/               # Next.js API routes (if needed)
├── components/            # Reusable React components
│   ├── ui/               # shadcn/ui components
│   ├── dashboard/        # Dashboard-specific components
│   ├── search/           # Search interface components
│   └── workspace/        # Workspace detail components
├── lib/                  # Utility functions and configurations
│   ├── api.ts           # API client and hooks
│   ├── utils.ts         # General utilities
│   └── validations.ts   # Form validation schemas
├── hooks/               # Custom React hooks
├── types/               # TypeScript type definitions
├── styles/              # Global styles and Tailwind config
└── public/              # Static assets
```

## Development Workflow

### Adding New Components

1. **Create the component** in the appropriate directory:
   ```tsx
   // components/ui/MyComponent.tsx
   import { cn } from "@/lib/utils"

   interface MyComponentProps {
     className?: string
   }

   export function MyComponent({ className }: MyComponentProps) {
     return (
       <div className={cn("my-component", className)}>
         Content
       </div>
     )
   }
   ```

2. **Add to component exports** if it's a shared component:
   ```tsx
   // components/ui/index.ts
   export { MyComponent } from "./MyComponent"
   ```

### Working with API Data

Use the provided API hooks for data fetching:

```tsx
// In a component
import { useWorkspaces, useWorkspaceProfile } from "@/lib/api"

function Dashboard() {
  const { data: workspaces, isLoading } = useWorkspaces()
  const { data: profile } = useWorkspaceProfile("workspace-id")

  if (isLoading) return <div>Loading...</div>

  return (
    <div>
      {workspaces?.map(workspace => (
        <div key={workspace.id}>{workspace.name}</div>
      ))}
    </div>
  )
}
```

### Styling Guidelines

- **Use Tailwind classes** for styling
- **Follow the design system** defined in `styles/globals.css`
- **Use CSS variables** for theming
- **Responsive design**: Mobile-first approach

```tsx
// Good example
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* Content */}
</div>
```

## Available Scripts

```bash
# Development
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run preview      # Preview production build

# Code Quality
npm run lint         # Run ESLint
npm run format       # Run Prettier
npm run type-check   # Run TypeScript type checking

# Testing
npm run test         # Run Jest tests
npm run test:watch   # Run tests in watch mode
npm run test:coverage # Run tests with coverage

# Storybook
npm run storybook    # Start Storybook development server
npm run build-storybook # Build Storybook for deployment
```

## Component Development

### Using Storybook

```bash
npm run storybook
```

Create stories for components:

```tsx
// components/MyComponent.stories.tsx
import type { Meta, StoryObj } from "@storybook/react"
import { MyComponent } from "./MyComponent"

const meta: Meta<typeof MyComponent> = {
  title: "Components/MyComponent",
  component: MyComponent,
  parameters: {
    layout: "centered",
  },
}

export default meta

type Story = StoryObj<typeof MyComponent>

export const Default: Story = {
  args: {
    // props
  },
}
```

## Testing

### Unit Tests

```tsx
// __tests__/MyComponent.test.tsx
import { render, screen } from "@testing-library/react"
import { MyComponent } from "@/components/MyComponent"

describe("MyComponent", () => {
  it("renders correctly", () => {
    render(<MyComponent />)
    expect(screen.getByText("Content")).toBeInTheDocument()
  })
})
```

### Integration Tests

```tsx
// __tests__/Dashboard.test.tsx
import { render, screen, waitFor } from "@testing-library/react"
import { Dashboard } from "@/components/Dashboard"

describe("Dashboard", () => {
  it("loads and displays workspaces", async () => {
    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText("Workspace 1")).toBeInTheDocument()
    })
  })
})
```

## Deployment

### Build for Production

```bash
npm run build
npm run start
```

### Environment Variables for Production

```bash
# .env.production
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_APP_ENV=production
```

### Docker Deployment (Optional)

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
CMD ["npm", "start"]
```

## Troubleshooting

### Common Issues

1. **API Connection Issues**
   - Ensure backend API is running on the correct port
   - Check CORS configuration in backend
   - Verify environment variables

2. **Build Errors**
   - Clear `.next` folder: `rm -rf .next`
   - Reinstall dependencies: `rm -rf node_modules && npm install`
   - Check TypeScript errors: `npm run type-check`

3. **Styling Issues**
   - Ensure Tailwind is properly configured
   - Check for CSS import in `_app.tsx`
   - Verify class names are correct

### Getting Help

- Check the [Next.js documentation](https://nextjs.org/docs)
- Review [Tailwind CSS docs](https://tailwindcss.com/docs)
- Check [shadcn/ui documentation](https://ui.shadcn.com)
- Look at existing components for patterns
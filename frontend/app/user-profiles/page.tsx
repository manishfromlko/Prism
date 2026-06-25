'use client'

import { useUserProfiles } from '@/hooks/use-api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Users } from 'lucide-react'

function ProfileCard({ profile }: { profile: { id: string; user_id: string; user_profile: string; tags: string[] } }) {
  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold text-sm shrink-0">
            {profile.user_id.split('.')[0]?.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <CardTitle className="text-base">{profile.user_id}</CardTitle>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-4 flex-1">
        <p className="text-sm text-muted-foreground leading-relaxed">
          {profile.user_profile}
        </p>

        {profile.tags.length > 0 && (
          <div className="mt-auto pt-2 border-t">
            <p className="text-xs font-medium text-muted-foreground mb-2">Tools & Technologies</p>
            <div className="flex flex-wrap gap-1.5">
              {profile.tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs px-2 py-0.5">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ProfileSkeleton() {
  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-full" />
          <Skeleton className="h-5 w-32" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/6" />
        <div className="pt-2 border-t mt-4 flex gap-1.5 flex-wrap">
          <Skeleton className="h-5 w-14 rounded-full" />
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-12 rounded-full" />
        </div>
      </CardContent>
    </Card>
  )
}

export default function UserProfilesPage() {
  const { data, isLoading, error } = useUserProfiles()

  const profiles = data?.data ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Users className="h-8 w-8" />
          User Profiles
        </h1>
        <p className="text-muted-foreground mt-1">
          AI-generated profiles of workspace members based on their notebooks, scripts, and tools.
        </p>
      </div>

      {isLoading ? (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(5)].map((_, i) => <ProfileSkeleton key={i} />)}
        </div>
      ) : error ? (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center">
          <p className="text-sm text-destructive font-medium">Failed to load user profiles</p>
          <p className="text-xs text-muted-foreground mt-1">
            Make sure the API server is running and the profile indexer has been executed.
          </p>
        </div>
      ) : profiles.length === 0 ? (
        <div className="rounded-lg border bg-muted/30 p-10 text-center">
          <Users className="mx-auto h-10 w-10 text-muted-foreground mb-3" />
          <p className="font-medium">No profiles found</p>
          <p className="text-sm text-muted-foreground mt-1">
            Run the profile indexer to generate user profiles from the catalog.
          </p>
          <code className="mt-3 block text-xs bg-muted rounded px-3 py-2 text-left max-w-md mx-auto">
            python3 -m src.retrieval.profile_indexer
          </code>
        </div>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            Showing {profiles.length} user profile{profiles.length !== 1 ? 's' : ''}
          </p>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {profiles.map((profile) => (
              <ProfileCard key={profile.id} profile={profile} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

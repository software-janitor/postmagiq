/**
 * API client for post metadata
 * Uses the workspace-scoped API for accurate post data
 */

import { apiGet } from './client'
import { useWorkspaceStore } from '../stores/workspaceStore'

// Database-backed post from workspace API
interface WorkspacePost {
  id: string
  workspace_id: string
  post_number: number
  chapter_id: string
  topic: string
  shape: string | null
  cadence: string | null
  entry_point: string | null
  status: string
  guidance: string | null
  story_used: string | null
  published_url: string | null
  assignee_id: string | null
  due_date: string | null
  priority: number | null
  estimated_hours: number | null
}

// Chapter info from strategy API
interface ChapterInfo {
  id: string
  chapter_number: number
  title: string
  theme: string | null
}

// Transformed post for workflow UI
export interface PostMetadata {
  post_id: string
  post_number: number
  chapter: number
  topic: string
  shape: string | null
  cadence: string | null
  entry_point: string | null
  status: string
  story_used: string | null
  enemy: string
  guidance: string
}

// Chapter enemies for guidance (fallback if not in strategy)
const CHAPTER_ENEMIES: Record<number, string> = {
  1: "Tool-first AI adoption (buying tools without an operating model)",
  2: "Unbounded autonomous agents (no blast radius, no checkpoints)",
  3: "AI adoption without domain expertise (AI can't validate what humans don't understand)",
  4: "Prompt engineering as strategy (optimizing prompts instead of building systems)",
  5: "Prompt engineering as strategy (optimizing prompts instead of building systems)",
  6: "AI adoption without enablement (shipping AI without training engineers)",
  7: "Scaling AI systems (guardrails + adoption at scale)",
  8: "Synthesis (all enemies)",
}

// Shape guidance
const SHAPE_GUIDANCE: Record<string, string> = {
  "FULL": `Tell a complete story with all 5 elements:
1. The Failure - What broke? What went wrong?
2. The Misunderstanding - What do people assume is the fix?
3. AI Amplification - How did AI make it worse?
4. The Fix - What resolved it?
5. The Scar - What did you learn?

Include specific details: error messages, hours lost, tools used.`,
  "PARTIAL": `Tell a story WITHOUT resolution:
1. The Failure - What broke?
2. The Misunderstanding - What's the wrong assumption?
3. AI Amplification - How did AI make it worse?

Do NOT include a fix or lesson. End messy. "I don't have a clean answer yet."`,
  "OBSERVATION": `Share something you noticed. No backstory needed, no lesson required.
- What did you observe?
- Why did it catch your attention?
- What questions does it raise?

End with a question or open thought.`,
  "SHORT": `One idea, under 200 words. No wrap-up needed.
- What's the single insight?
- One concrete example or moment
- Just end. No conclusion.`,
}

// Cache for chapter info to avoid multiple API calls
let chaptersCache: Map<string, ChapterInfo> | null = null

async function getChapterInfo(workspaceId: string): Promise<Map<string, ChapterInfo>> {
  if (chaptersCache) return chaptersCache

  try {
    const chapters = await apiGet<ChapterInfo[]>(`/v1/w/${workspaceId}/chapters`)
    chaptersCache = new Map(chapters.map(c => [c.id, c]))
    return chaptersCache
  } catch {
    return new Map()
  }
}

function transformPost(post: WorkspacePost, chapters: Map<string, ChapterInfo>): PostMetadata {
  const chapter = chapters.get(post.chapter_id)
  const chapterNumber = chapter?.chapter_number || 1
  const enemy = chapter?.theme || CHAPTER_ENEMIES[chapterNumber] || ""
  const shapeGuidance = SHAPE_GUIDANCE[post.shape || "FULL"] || SHAPE_GUIDANCE["FULL"]
  const guidance = post.guidance || `**Chapter Enemy:** ${enemy}\n\n${shapeGuidance}`

  return {
    post_id: `post_${post.post_number.toString().padStart(2, '0')}`,
    post_number: post.post_number,
    chapter: chapterNumber,
    topic: post.topic,
    shape: post.shape,
    cadence: post.cadence,
    entry_point: post.entry_point,
    status: post.status.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()),
    story_used: post.story_used,
    enemy,
    guidance,
  }
}

export async function fetchAvailablePosts(): Promise<PostMetadata[]> {
  const workspaceId = useWorkspaceStore.getState().currentWorkspaceId
  if (!workspaceId) return []

  // Fetch posts and chapters
  const [posts, chapters] = await Promise.all([
    apiGet<WorkspacePost[]>(`/v1/w/${workspaceId}/posts`),
    getChapterInfo(workspaceId),
  ])

  // Filter to posts that need work
  const availableStatuses = ['needs_story', 'not_started', 'draft', 'in_progress']
  const available = posts.filter(p =>
    availableStatuses.some(s => p.status.toLowerCase().includes(s.replace('_', ' ')) ||
                                p.status.toLowerCase() === s)
  )

  return available.map(p => transformPost(p, chapters)).sort((a, b) => a.post_number - b.post_number)
}

export async function fetchAllPosts(): Promise<PostMetadata[]> {
  const workspaceId = useWorkspaceStore.getState().currentWorkspaceId
  if (!workspaceId) return []

  const [posts, chapters] = await Promise.all([
    apiGet<WorkspacePost[]>(`/v1/w/${workspaceId}/posts`),
    getChapterInfo(workspaceId),
  ])

  return posts.map(p => transformPost(p, chapters)).sort((a, b) => a.post_number - b.post_number)
}

export async function fetchNextPost(): Promise<PostMetadata | null> {
  const available = await fetchAvailablePosts()
  if (!available.length) return null
  return available[0]
}

export async function fetchPost(postId: string): Promise<PostMetadata | null> {
  const posts = await fetchAllPosts()
  return posts.find(p => p.post_id === postId) || null
}

// Clear the chapters cache when needed (e.g., after strategy update)
export function clearChaptersCache() {
  chaptersCache = null
}

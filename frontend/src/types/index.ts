export interface Stream {
  id: number
  channel_id: number
  platform: 'youtube' | 'bilibili'
  video_id: string | null
  title: string | undefined
  thumbnail_url: string | null
  viewer_count: number
  status: 'live' | 'upcoming' | 'archive' | 'offline'
  started_at: string | null
  scheduled_at: string | undefined
  ended_at: string | null
  live_chat_id: string | null
  channel_name: string | null
  channel_avatar: string | null
  channel_avatar_shape?: 'circle' | 'square'
  org_id?: number | null
}

export type StreamStatus = 'live' | 'upcoming' | 'archive' | 'offline'

export interface Channel {
  id: number
  platform: 'youtube' | 'bilibili' | 'empty'
  channel_id: string
  name: string
  avatar_url: string | null
  is_active: boolean
  org_id: number | null
  avatar_shape: 'circle' | 'square'
  banner_url: string | null
  twitter_url: string | null
  youtube_url: string | null
  twitch_url: string | null
  description: string | null
  group: string | null
  status: string
  is_liked: boolean
  is_blocked: boolean
  bilibili_sign: string | null
  bilibili_fans: number | null
  bilibili_archive_count: number | null
  subscriber_count: number | null
}

export interface ChannelCreate {
  platform: 'youtube' | 'bilibili'
  channel_id: string
  name: string
  avatar_url?: string | null
  is_active?: boolean
  org_id?: number | null
  avatar_shape?: 'circle' | 'square'
  twitter_url?: string | null
  youtube_url?: string | null
}

export interface Organization {
  id: number
  name: string
  name_en: string | null
  logo_url: string | null
  website: string | null
  logo_shape: 'circle' | 'square'
}

export interface Video {
  id: string
  title: string
  thumbnail_url: string | undefined
  duration: string | null
  view_count: number
  published_at: string | null
  status: string
}

export interface PaginatedVideos {
  videos: Video[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface VideoFetchState {
  videos: import('vue').Ref<Video[]>
  page: import('vue').Ref<number>
  totalPages: import('vue').Ref<number>
  loading: import('vue').Ref<boolean>
  fetch: (channelId: number) => Promise<void>
  reset: () => void
}

export interface FetchConfig {
  status: string | string[]
  pageSize?: number
  mergeSort?: (a: Video, b: Video) => number
}

export interface ContentNode {
  type: 'text' | 'emoji' | 'at'
  text: string
  url?: string
  rid?: string
}

export interface BilibiliInfo {
  info: {
    mid: number
    name: string
    sex: string
    face: string
    sign: string
    level: number
    fans: number
    attention: number
    archive_count: number
    article_count: number
    following: number
    like_num: number
    official_verify: { type: number; desc: string } | null
  } | null
  dynamics: Array<{
    dynamic_id: string
    url: string
    uid: string
    uname: string
    face: string
    type: number
    timestamp: number
    content_nodes: ContentNode[]
    images: string[]
    repost_content: string | null
    stat: {
      forward: number
      comment: number
      like: number
    }
    topic: string
    is_top: boolean
  }>
  videos: Array<{
    bvid: string
    title: string
    pic: string
    aid: number
    duration: string
    pubdate: number
    play: number
    like: number
    coin: number
    favorite: number
    share: number
    reply: number
  }>
  next_offset: string
}

export interface Role {
  id: number
  name: string
  description: string | null
}

export interface Permission {
  id: number
  name: string
  description: string | null
  resource: string
  action: string
}

export interface UserWithRoles {
  id: number
  username: string
  email: string | null
  created_at: string
  roles: string[]
}

export interface User {
  id: number
  username: string
  email: string | null
  avatar: string
  created_at: string
  roles: string[]
  permissions?: string[]
}

export interface BilibiliGuard {
  canAccess: import('vue').ComputedRef<boolean>
  filterStreams: (streams: Stream[]) => Stream[]
  filterChannels: (channels: Channel[]) => Channel[]
  platformOptions: import('vue').ComputedRef<{ label: string; value: string }[]>
}

export interface BilibiliInfoData {
  mid: number
  name: string
  face: string | undefined
  sign: string | null
  fans: number | undefined
  attention: number | null
  archive_count: number | null
}

export interface BilibiliVideosData {
  videos: Array<{
    bvid: string
    title: string
    pic: string
    aid: number
    duration: string
    pubdate: number
    play: number
  }>
  total: number
}

export interface BilibiliDynamicsData {
  dynamics: Array<{
    dynamic_id: string
    url: string
    uid: string
    uname: string
    face: string
    type: number
    timestamp: number
    content_nodes: ContentNode[]
    images: string[]
    repost_content: string | null
    stat: {
      forward: number
      comment: number
      like: number
    }
    topic: string
    is_top: boolean
  }>
  next_offset: string
}
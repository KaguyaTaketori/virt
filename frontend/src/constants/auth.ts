export const ROLES = {
  SUPERADMIN: 'superadmin',
  ADMIN:      'admin',
  OPERATOR:   'operator',
  USER:       'user',
} as const

export const PERMISSIONS = {
  BILIBILI_ACCESS: 'bilibili.access',
  CHANNEL_MANAGE:  'channel.manage',
} as const

export type RoleName = typeof ROLES[keyof typeof ROLES]
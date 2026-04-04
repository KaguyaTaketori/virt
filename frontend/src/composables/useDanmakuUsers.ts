import { ref, computed } from 'vue'

const STORAGE_KEY_BLOCKED    = 'danmaku_blocked_users'
const STORAGE_KEY_HIGHLIGHTED = 'danmaku_highlighted_users'

const _blocked     = ref<Set<string>>(loadSet(STORAGE_KEY_BLOCKED))
const _highlighted = ref<Set<string>>(loadSet(STORAGE_KEY_HIGHLIGHTED))

function loadSet(key: string): Set<string> {
  try {
    const raw = localStorage.getItem(key)
    return raw ? new Set(JSON.parse(raw)) : new Set()
  } catch {
    return new Set()
  }
}

function saveSet(key: string, set: Set<string>) {
  try {
    localStorage.setItem(key, JSON.stringify([...set]))
  } catch { /* ignore */ }
}

export function useDanmakuUsers() {
  const blockedUsers     = computed(() => _blocked.value)
  const highlightedUsers = computed(() => _highlighted.value)

  function blockUser(userId: string) {
    if (!userId) return
    _blocked.value = new Set([..._blocked.value, userId])
    // 屏蔽时自动取消高亮
    _highlighted.value.delete(userId)
    _highlighted.value = new Set(_highlighted.value)
    saveSet(STORAGE_KEY_BLOCKED, _blocked.value)
    saveSet(STORAGE_KEY_HIGHLIGHTED, _highlighted.value)
  }

  function unblockUser(userId: string) {
    _blocked.value.delete(userId)
    _blocked.value = new Set(_blocked.value)
    saveSet(STORAGE_KEY_BLOCKED, _blocked.value)
  }

  function highlightUser(userId: string) {
    if (!userId) return
    _highlighted.value = new Set([..._highlighted.value, userId])
    saveSet(STORAGE_KEY_HIGHLIGHTED, _highlighted.value)
  }

  function unhighlightUser(userId: string) {
    _highlighted.value.delete(userId)
    _highlighted.value = new Set(_highlighted.value)
    saveSet(STORAGE_KEY_HIGHLIGHTED, _highlighted.value)
  }

  function isBlocked(userId: string): boolean {
    return _blocked.value.has(userId)
  }

  function isHighlighted(userId: string): boolean {
    return _highlighted.value.has(userId)
  }

  function clearAll() {
    _blocked.value = new Set()
    _highlighted.value = new Set()
    localStorage.removeItem(STORAGE_KEY_BLOCKED)
    localStorage.removeItem(STORAGE_KEY_HIGHLIGHTED)
  }

  return {
    blockedUsers,
    highlightedUsers,
    blockUser,
    unblockUser,
    highlightUser,
    unhighlightUser,
    isBlocked,
    isHighlighted,
    clearAll,
  }
}
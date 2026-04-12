import { computed } from 'vue'
import { useLocalStorage } from '@vueuse/core'

const STORAGE_KEY_BLOCKED = 'danmaku_blocked_users'
const STORAGE_KEY_HIGHLIGHTED = 'danmaku_highlighted_users'

const setSerializer = {
  read: (v: string) => v ? new Set<string>(JSON.parse(v)) : new Set<string>(),
  write: (v: Set<string>) => JSON.stringify(Array.from(v)),
}

const _blocked = useLocalStorage<Set<string>>(STORAGE_KEY_BLOCKED, new Set(), {
  serializer: setSerializer,
})

const _highlighted = useLocalStorage<Set<string>>(STORAGE_KEY_HIGHLIGHTED, new Set(), {
  serializer: setSerializer,
})

export function useDanmakuUsers() {
  const blockedUsers = computed(() => _blocked.value)
  const highlightedUsers = computed(() => _highlighted.value)

  function blockUser(userId: string) {
    if (!userId || _blocked.value.has(userId)) return
    
    const nextBlocked = new Set(_blocked.value)
    nextBlocked.add(userId)
    _blocked.value = nextBlocked

    if (_highlighted.value.has(userId)) {
      unhighlightUser(userId)
    }
  }

  function unblockUser(userId: string) {
    if (!_blocked.value.has(userId)) return
    const next = new Set(_blocked.value)
    next.delete(userId)
    _blocked.value = next
  }

  function highlightUser(userId: string) {
    if (!userId || _highlighted.value.has(userId)) return
    if (_blocked.value.has(userId)) return

    const next = new Set(_highlighted.value)
    next.add(userId)
    _highlighted.value = next
  }

  function unhighlightUser(userId: string) {
    if (!_highlighted.value.has(userId)) return
    const next = new Set(_highlighted.value)
    next.delete(userId)
    _highlighted.value = next
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
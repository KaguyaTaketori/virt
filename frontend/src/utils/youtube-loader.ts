export interface YTPlayer {
  destroy(): void;
  loadVideoById(id: string | { videoId: string; startSeconds?: number }): void;
  getCurrentTime(): number;
  playVideo(): void;
  pauseVideo(): void;
  setVolume(volume: number): void;
}

export interface YTNamespace {
  Player: new (element: HTMLElement | string, options: any) => YTPlayer;
}

// 扩展全局 Window 接口
declare global {
  interface Window {
    YT: YTNamespace;
    onYouTubeIframeAPIReady?: () => void;
  }
}

let isApiLoading = false
let apiPromise: Promise<void> | null = null

export function loadYouTubeIframeAPI(): Promise<void> {
  if (window.YT && window.YT.Player) {
    return Promise.resolve()
  }

  if (apiPromise) {
    return apiPromise
  }

  apiPromise = new Promise((resolve, reject) => {
    isApiLoading = true
    const previousHandler = window.onYouTubeIframeAPIReady
    window.onYouTubeIframeAPIReady = () => {
      if (previousHandler) previousHandler()
      resolve()
    }

    const tag = document.createElement('script')
    tag.src = 'https://www.youtube.com/iframe_api'
    tag.onerror = (err) => {
      apiPromise = null
      isApiLoading = false
      reject(err)
    }

    const firstScriptTag = document.getElementsByTagName('script')[0]
    if (firstScriptTag?.parentNode) {
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag)
    } else {
      document.head.appendChild(tag)
    }
  })

  return apiPromise
}
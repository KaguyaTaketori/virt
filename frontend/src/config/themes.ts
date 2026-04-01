export interface Theme {
  id: string
  name: string
  colors: {
    primary: string
    primaryHover: string
    secondary: string
  }
}

export const themes: Theme[] = [
  {
    id: 'default',
    name: '默认 (粉色)',
    colors: {
      primary: '#ec4899',
      primaryHover: '#f472b6',
      secondary: '#3b88d5'
    }
  },
  {
    id: 'matsuri',
    name: '夏色祭',
    colors: {
      primary: '#faa749',
      primaryHover: '#fbbf24',
      secondary: '#82D251'
    }
  },
  {
    id: 'pekora',
    name: '兔田ぺこら',
    colors: {
      primary: '#DC8C2C',
      primaryHover: '#e8a23d',
      secondary: '#439369'
    }
  },
  {
    id: 'korone',
    name: '戌神沁音',
    colors: {
      primary: '#B07975',
      primaryHover: '#c9908a',
      secondary: '#D57E3D'
    }
  },
  {
    id: 'fubuki',
    name: '白上吹雪',
    colors: {
      primary: '#9E8461',
      primaryHover: '#b89a75',
      secondary: '#83B0BD'
    }
  },
  {
    id: 'rushia',
    name: '潤羽るしあ',
    colors: {
      primary: '#22C4AC',
      primaryHover: '#2ed4bc',
      secondary: '#5783BF'
    }
  },
  {
    id: 'suisei',
    name: '星街すいせい',
    colors: {
      primary: '#a8d6fc',
      primaryHover: '#c0e2fd',
      secondary: '#3c3a97'
    }
  },
  {
    id: 'coco',
    name: '桐生ここ',
    colors: {
      primary: '#D3B633',
      primaryHover: '#e0c449',
      secondary: '#FF9A63'
    }
  },
  {
    id: 'okayu',
    name: '猫又おかゆ',
    colors: {
      primary: '#cda4d5',
      primaryHover: '#dbb5e0',
      secondary: '#4a477c'
    }
  },
  {
    id: 'lamy',
    name: '雪花ラミィ',
    colors: {
      primary: '#338bcc',
      primaryHover: '#449dd4',
      secondary: '#72b0e4'
    }
  }
]

export const defaultTheme = themes[0]
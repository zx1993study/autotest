export const appBase = import.meta.env.BASE_URL

export function appPath(path: string): string {
  return `${appBase}${path.replace(/^\/+/, '')}`
}

export function routerPath(path: string): string | null {
  if (!path.startsWith(appBase)) return null
  return `/${path.slice(appBase.length)}`
}

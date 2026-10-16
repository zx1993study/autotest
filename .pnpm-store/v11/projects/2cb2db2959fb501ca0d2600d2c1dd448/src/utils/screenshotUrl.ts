import { readSessionValue } from './browserSession'
import { appPath } from './appBase'

export function withScreenshotAccessToken(url: string) {
  if (!url || url.startsWith('data:') || url.startsWith('blob:')) {
    return url
  }
  const resolved = url.startsWith('/api/v1/') ? appPath(url) : url
  const parsed = new URL(resolved, window.location.origin)
  if (parsed.origin !== window.location.origin || (!parsed.pathname.startsWith(appPath('/api/v1/screenshots/')) && !parsed.pathname.startsWith(appPath('/api/v1/app-recordings/')))) {
    return resolved
  }
  const token = readSessionValue('access_token')
  if (!token || /[?&]access_token=/.test(url)) {
    return resolved
  }
  return `${resolved}${resolved.includes('?') ? '&' : '?'}access_token=${encodeURIComponent(token)}`
}

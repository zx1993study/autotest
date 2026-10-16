export function isLoginTarget(url: string): boolean {
  try {
    const parsed = new URL(url, 'https://discovery.invalid')
    const hashRoute = parsed.hash.replace(/^#!?/, '').split('?')[0]
    return [parsed.pathname, hashRoute].some(route => /(^|\/)(login|signin|sign-in)(\/|$)/i.test(route))
  } catch { return false }
}

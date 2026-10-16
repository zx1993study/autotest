export function downloadBundle(file: { bundle_filename: string; bundle_base64: string }) {
  const data = Uint8Array.from(atob(file.bundle_base64), char => char.charCodeAt(0))
  const url = URL.createObjectURL(new Blob([data], { type: 'application/zip' }))
  const link = document.createElement('a')
  link.href = url
  link.download = file.bundle_filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

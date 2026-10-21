function installGuard(owner = 'default') {
  const app = getApp();
  if (app.__fieldworkUITestGuard) throw new Error('A test guard is already installed');
  const request = wx.request;
  const upload = wx.uploadFile;
  const guard = { owner, blocked: [], errors: [], pending: 0, changed: Date.now(), request, upload };
  app.__fieldworkUITestGuard = guard;
  function endpoint(url) {
    return String(url || '').split('?')[0].replace(/^https?:\/\/[^/]+/, '');
  }
  wx.request = function guardedRequest(options) {
    const method = String(options.method || 'GET').toUpperCase();
    guard.changed = Date.now();
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
      guard.blocked.push({ method, path: endpoint(options.url) });
      const error = { errMsg: 'request:fail blocked by read-only UI test' };
      options.fail?.(error);
      options.complete?.(error);
      return { abort() {}, onHeadersReceived() {}, offHeadersReceived() {} };
    }
    guard.pending++;
    return request.call(wx, { ...options,
      success(response) {
        const data = response.data;
        if (response.statusCode >= 400 || (data && typeof data === 'object'
          && (data.success === false || (data.code !== undefined && ![200, '200'].includes(data.code))))) {
          guard.errors.push({ path: endpoint(options.url), status: response.statusCode });
        }
        options.success?.(response);
      },
      fail(error) {
        guard.errors.push({ path: endpoint(options.url), error: 'request failed' });
        options.fail?.(error);
      },
      complete(result) {
        guard.pending--;
        guard.changed = Date.now();
        options.complete?.(result);
      }
    });
  };
  wx.uploadFile = function guardedUpload(options) {
    guard.blocked.push({ method: 'UPLOAD', path: endpoint(options.url) });
    const error = { errMsg: 'uploadFile:fail blocked by read-only UI test' };
    options.fail?.(error);
    options.complete?.(error);
    return { abort() {} };
  };
  if (wx.request === request || wx.uploadFile === upload) throw new Error('Unable to install network guard');
  return true;
}

function readGuard(reset = false) {
  const guard = getApp().__fieldworkUITestGuard;
  if (!guard) throw new Error('Missing network guard');
  const result = { blocked: guard.blocked.slice(), errors: guard.errors.slice(), pending: guard.pending, changed: guard.changed };
  if (reset) {
    if (guard.pending) throw new Error('Cannot reset with pending read requests');
    guard.blocked = [];
    guard.errors = [];
    guard.changed = Date.now();
  }
  return result;
}

function restoreGuard(owner = 'default') {
  const app = getApp();
  const guard = app.__fieldworkUITestGuard;
  if (!guard || guard.owner !== owner) return;
  wx.request = guard.request;
  wx.uploadFile = guard.upload;
  delete app.__fieldworkUITestGuard;
}

module.exports = { installGuard, readGuard, restoreGuard };

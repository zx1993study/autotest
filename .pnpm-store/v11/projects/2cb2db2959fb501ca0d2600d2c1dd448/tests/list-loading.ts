import { CanceledError } from 'axios'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { createApp, h } from 'vue'

import { apiClient, request } from '../src/api/client'
import { useLatestRequest } from '../src/composables/useLatestRequest'
import { clearRemoteOptionsCache, createResource, listRemoteOptionsCached } from '../src/services/resource.service'
import { useAuthStore } from '../src/store/auth'
import { requestStore } from '../src/store/request'

type Check = { name: string; passed: true }

function assert(value: unknown, message: string) {
  if (!value) throw new Error(message)
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: unknown) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

function mountRequest() {
  let state!: ReturnType<typeof useLatestRequest>
  const element = document.createElement('div')
  document.body.append(element)
  const app = createApp({ setup() { state = useLatestRequest(); return () => h('span') } })
  app.mount(element)
  return { state, destroy() { app.unmount(); element.remove() } }
}

async function checkRequestOrdering(): Promise<Check> {
  const { state, destroy } = mountRequest()
  let current = ''
  const apply = (value: string) => { current = value }
  try {
    const old = deferred<string>(), latest = deferred<string>()
    let oldSignal!: AbortSignal
    const first = state.run(signal => { oldSignal = signal; return old.promise }, apply)
    const second = state.run(() => latest.promise, apply)
    assert(oldSignal.aborted, 'superseded request must be aborted')
    old.reject(new Error('obsolete failure'))
    await first
    assert(state.loading.value && state.error.value === '', 'obsolete failure/finally changed active request')
    latest.resolve('latest')
    await second
    assert(current === 'latest' && !state.loading.value, 'latest result was not applied')
    const stale = deferred<string>()
    const third = state.run(() => stale.promise, apply)
    await state.run(() => Promise.resolve('newest'), apply)
    stale.resolve('stale')
    await third
    assert(current === 'newest', 'late success overwrote newest result')
    await state.run(() => Promise.reject(new Error('current failure')), apply)
    assert(state.error.value === 'current failure' && !state.loading.value, 'current failure is missing')
    await state.run(() => Promise.resolve('retry'), apply)
    assert(current === 'retry' && state.error.value === '', 'retry did not clear current error')
    return { name: 'latest success, failure, finally and retry isolation', passed: true }
  } finally { destroy() }
}

async function checkUnmount(): Promise<Check> {
  const { state, destroy } = mountRequest()
  const pending = deferred<string>()
  let applied = false, signal!: AbortSignal
  const task = state.run(value => { signal = value; return pending.promise }, () => { applied = true })
  destroy()
  assert(signal.aborted && !state.loading.value, 'unmount must abort and stop loading')
  pending.resolve('late')
  await task
  assert(!applied && state.error.value === '', 'unmounted component accepted a late result')
  await state.run(() => { throw new Error('disposed request was started') }, () => { applied = true })
  assert(state.error.value === '', 'disposed component started a new request')
  return { name: 'unmount cancels outstanding request', passed: true }
}

function response(config: InternalAxiosRequestConfig, label: string): AxiosResponse {
  return { config, status: 200, statusText: 'OK', headers: {},
    data: { code: 0, message: 'success', data: [{ id: 1, name: label }] } }
}

function mockOptions() {
  const pending: { config: InternalAxiosRequestConfig; task: ReturnType<typeof deferred<AxiosResponse>> }[] = []
  apiClient.defaults.adapter = config => {
    const task = deferred<AxiosResponse>()
    pending.push({ config, task })
    return task.promise
  }
  async function flush() { for (let i = 0; i < 5; i += 1) await Promise.resolve() }
  function resolve(index: number, label: string) {
    const call = pending[index]
    call.task.resolve(response(call.config, label))
  }
  return { pending, resolve, flush }
}

async function checkOptionsCache(): Promise<Check> {
  clearRemoteOptionsCache()
  const mock = mockOptions(), originalNow = Date.now
  let now = 1000
  Date.now = () => now
  try {
    const first = listRemoteOptionsCached('/test/options', { b: 2, a: 1 })
    const second = listRemoteOptionsCached('/test/options', { a: 1, b: 2, empty: '' })
    await mock.flush()
    assert(mock.pending.length === 1, 'equivalent in-flight options were not deduplicated')
    mock.resolve(0, 'first')
    await Promise.all([first, second])
    await listRemoteOptionsCached('/test/options', { a: 1, b: 2 })
    assert(mock.pending.length === 1, 'fresh cache was not reused')
    now += 30_001
    const expired = listRemoteOptionsCached('/test/options', { a: 1, b: 2 })
    await mock.flush()
    assert(mock.pending.length === 2, 'expired entry did not reload')
    mock.resolve(1, 'expired')
    await expired
    useAuthStore().clearSession()
    const afterLogout = listRemoteOptionsCached('/test/options', { a: 1, b: 2 })
    await mock.flush()
    assert(mock.pending.length === 3, 'logout did not invalidate cached options')
    mock.resolve(2, 'logout')
    await afterLogout
    return { name: 'option request deduplication, TTL and logout invalidation', passed: true }
  } finally { Date.now = originalNow; clearRemoteOptionsCache() }
}

async function checkCacheInvalidation(): Promise<Check> {
  clearRemoteOptionsCache()
  const mock = mockOptions()
  const old = listRemoteOptionsCached('/test/options')
  await mock.flush()
  clearRemoteOptionsCache('/test/options')
  const fresh = listRemoteOptionsCached('/test/options')
  await mock.flush()
  mock.resolve(1, 'fresh')
  await fresh
  mock.resolve(0, 'old')
  await old
  assert((await listRemoteOptionsCached('/test/options'))[0].name === 'fresh', 'invalidated request repopulated cache')
  clearRemoteOptionsCache()
  const failed = listRemoteOptionsCached('/test/options').catch(() => null)
  await mock.flush()
  mock.pending[2].task.reject(new Error('temporary error'))
  await failed
  const retry = listRemoteOptionsCached('/test/options')
  await mock.flush()
  assert(mock.pending.length === 4, 'failed entry prevented retry')
  mock.resolve(3, 'retry')
  await retry
  return { name: 'in-flight invalidation and failed-cache retry', passed: true }
}

async function checkCancellation(): Promise<Check> {
  apiClient.defaults.adapter = () => Promise.reject(new CanceledError('cancelled'))
  await request({ url: '/test/cancelled' }).catch(() => undefined)
  assert(requestStore.lastError.value === null, 'cancellation leaked into global error')
  assert(requestStore.activeRequests.value === 0, 'request count did not settle')
  return { name: 'cancelled requests do not set global error', passed: true }
}

async function checkWriteInvalidation(): Promise<Check> {
  clearRemoteOptionsCache()
  const mock = mockOptions()
  const initial = listRemoteOptionsCached('/projects/options')
  await mock.flush()
  mock.resolve(0, 'initial')
  await initial
  const write = createResource('/projects', { name: 'Test', data: {} })
  await mock.flush()
  mock.resolve(1, 'created')
  await write
  const refreshed = listRemoteOptionsCached('/projects/options')
  await mock.flush()
  assert(mock.pending.length === 3, 'successful resource write did not invalidate options')
  mock.resolve(2, 'refreshed')
  await refreshed
  return { name: 'resource writes invalidate option cache', passed: true }
}

async function runChecks() {
  const adapter = apiClient.defaults.adapter
  try {
    return [await checkRequestOrdering(), await checkUnmount(), await checkOptionsCache(),
      await checkCacheInvalidation(), await checkWriteInvalidation(), await checkCancellation()]
  } finally { apiClient.defaults.adapter = adapter; clearRemoteOptionsCache() }
}

Object.assign(window, { runListLoadingChecks: runChecks })

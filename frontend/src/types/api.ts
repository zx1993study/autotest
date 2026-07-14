export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

export interface ApiResult<T> {
  code: number
  message: string
  data: T
}

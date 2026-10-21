export interface ExecutionAssertionView {
  definition: Record<string, unknown>
  outcome: 'passed' | 'failed' | 'unknown'
}

export interface ExecutionEvidence {
  request: unknown
  response: unknown
  assertions: ExecutionAssertionView[]
  httpStatus: unknown
  businessCode: unknown
  duration: unknown
  error: string
}

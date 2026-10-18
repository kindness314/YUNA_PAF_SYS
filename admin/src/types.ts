/** 后端 wire 契约（与 server/app/schemas.py 对应） */

export interface Batch {
  id: number
  name: string
  year: number
  stage: string
  is_active: boolean
  created_at: string | null
}

export interface DeptStat {
  dept: string
  applied: number
  exempt_exam: number
  submitted: number
  advanced: number
  admitted: number
}

export type FunnelKey = 'applied' | 'submitted' | 'advanced' | 'interviewed' | 'admitted'

export interface BatchStats {
  batch_id: number
  funnel: Record<FunnelKey, number>
  dept_stats: DeptStat[]
}

export interface Application {
  id: number
  batch_id: number
  student_no: string
  name: string
  phone: string
  dept_choice: string
  source: string
  exempt_exam: boolean
  status: string
  extra: Record<string, unknown>
  created_at: string | null
}

export interface Group {
  id: number
  batch_id: number
  name: string
  seq: number
}

export interface QueueEntry {
  id: number
  group_id: number
  application_id: number
  seq: number
  status: string
  room: string | null
}

export interface FormTemplate {
  id: number
  batch_id: number
  kind: string
  name: string
  version: number
  schema_json: { rule?: unknown[] }
}

/** fc-designer 组件 ref 的操作面 */
export interface DesignerHandle {
  getRule(): unknown[]
  setRule(rule: unknown[]): void
}

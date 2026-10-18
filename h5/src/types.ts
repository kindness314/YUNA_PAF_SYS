/** 后端 wire 契约（与 server/app/schemas.py 对应） */

export interface Batch {
  id: number
  name: string
  year: number
  stage: string
  is_active: boolean
}

export interface FormTemplate {
  id: number
  batch_id: number
  kind: string
  name: string
  version: number
  schema_json: { rule?: unknown[] }
}

export interface Application {
  id: number
  exempt_exam: boolean
}

/** form-create 组件 api 引用 */
export interface FormApi {
  validate(): Promise<unknown>
}

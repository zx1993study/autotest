import type { GenerationMessage } from './generation'

export type AppLivePhase = 'connecting'|'waiting_app'|'waiting_app_confirmation'|'observing'|'planning'|'ready'|'executing'|'waiting_next'|'waiting_user'|'waiting_manual'|'waiting_approval'|'paused'|'saving'|'finishing'|'canceled'
export interface AppExploration {
  id:number
  status:string
  feature_id:number
  device_id:number
  device_name:string
  entry_id:number
  bundle_id:string
  error?:string
  saved_resource?:{id:number;domain:string}
  live:{
    phase:AppLivePhase
    cursor:number
    revision:number
    conversation:GenerationMessage[]
    steps:Record<string,any>[]
    timeline:Record<string,any>[]
    input_info:Record<string,any>
    model_http_calls:number
    session_reused?:boolean
    connection?:{wda_url:string;status:string;checked_at:string}
    app_candidate?:{bundle_id:string;app_name:string;observed_at:string}|null
    outcome_unknown?:boolean
    nonce?:string
    preview?:{screenshot_url?:string}
    observed_at?:string
    events:{label:string;status:string;time:string}[]
    command?:{step:Record<string,any>;target_id?:number}
  }
  result?:{records:Record<string,any>[]}
}

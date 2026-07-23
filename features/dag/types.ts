
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
export type RunStatus  = 'queued' | 'active' | 'completed' | 'failed';
export type StreamStatus = 'idle' | 'connecting' | 'live' | 'done' | 'error';

export interface DAGRun {
  id:           number;
  objective:    string;
  status:       RunStatus;
  started_at?:  string;
  created_at?:  string;
  completed_at?: string | null;
  agent_id?:    string;
  task_count?:  number;
  tasks?: Array<{
    id: string | number;
    dag_id?: string;
    status: string;
  }>;
  task_counts?: {
    total:     number;
    completed: number;
    failed:    number;
    running:   number;
    pending:   number;
  };
}

export interface TaskRecord {
  id:           number;
  run_id:       number;
  task_dag_id:  string;
  action:       string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  args:         Record<string, any>;
  status:       TaskStatus;
  result:       string | null;
  error:        string | null;
  start_time:   string | null;
  end_time:     string | null;
  retry_count?: number;
}

export interface LiveTaskState {
  task_dag_id: string;
  action:      string;
  status:      TaskStatus;
  result:      string | null;
  error:       string | null;
  start_time:  string | null;
  end_time:    string | null;
}

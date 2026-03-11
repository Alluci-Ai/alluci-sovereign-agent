
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
export type RunStatus  = 'queued' | 'active' | 'completed' | 'failed';
export type StreamStatus = 'idle' | 'connecting' | 'live' | 'done' | 'error';

export interface DAGRun {
  id:           number;
  objective:    string;
  status:       RunStatus;
  started_at:   string;
  completed_at: string | null;
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

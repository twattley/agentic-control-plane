import type {
  DecisionInput,
  EventInput,
  QueueName,
  Run,
  RunDetail,
} from '@agentic-control-plane/domain-types'
import { useMutation, useQuery } from '@tanstack/react-query'
import { apiFetch, apiPost } from './http'
import { queryClient } from './queryClient'

const QUEUES: QueueName[] = ['review', 'fix', 'human']

export function useQueue(name: QueueName) {
  return useQuery({
    queryKey: ['queue', name],
    queryFn: () => apiFetch<Run[]>(`/queue/${name}`),
    refetchInterval: 5_000, // the inbox should feel live
  })
}

export function useRun(id: number) {
  return useQuery({
    queryKey: ['run', id],
    queryFn: () => apiFetch<RunDetail>(`/runs/${id}`),
    refetchInterval: 5_000,
  })
}

function invalidateRun(id: number) {
  queryClient.invalidateQueries({ queryKey: ['run', id] })
  QUEUES.forEach((q) => queryClient.invalidateQueries({ queryKey: ['queue', q] }))
}

export function useDecide(id: number) {
  return useMutation({
    mutationFn: (body: DecisionInput) => apiPost<Run>(`/runs/${id}/decision`, body),
    onSuccess: () => invalidateRun(id),
  })
}

export function usePostEvent(id: number) {
  return useMutation({
    mutationFn: (body: EventInput) => apiPost(`/runs/${id}/events`, body),
    onSuccess: () => invalidateRun(id),
  })
}

// Manual self-heal: re-dispatch the agent the current state is waiting on.
export function useDispatch(id: number) {
  return useMutation({
    mutationFn: () => apiPost(`/runs/${id}/dispatch`, {}),
    onSuccess: () => invalidateRun(id),
  })
}

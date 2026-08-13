import type {
  BoardPane,
  DecisionInput,
  EventInput,
  QueueName,
  Repo,
  Run,
  RunDetail,
  RunInput,
  Ticket,
  TicketDetail,
} from '@agentic-control-plane/domain-types'
import { useMutation, useQuery } from '@tanstack/react-query'
import { apiFetch, apiPost } from './http'
import { queryClient } from './queryClient'

const QUEUES: QueueName[] = ['review', 'fix', 'human']

export function useRepos() {
  // Listing is also the sync: the API scans the Projects folder on every read,
  // so a freshly-cloned repo appears within one refetch.
  return useQuery({
    queryKey: ['repos'],
    queryFn: () => apiFetch<Repo[]>('/repos'),
    refetchInterval: 15_000,
  })
}

export function useRepo(id: number) {
  return useQuery({ queryKey: ['repo', id], queryFn: () => apiFetch<Repo>(`/repos/${id}`) })
}

export function useBoard() {
  return useQuery({
    queryKey: ['board'],
    queryFn: () => apiFetch<BoardPane[]>('/board'),
    refetchInterval: 5_000, // agents move runs along in the background
  })
}

export function useTickets(repoId: number) {
  return useQuery({
    queryKey: ['tickets', repoId],
    queryFn: () => apiFetch<Ticket[]>(`/repos/${repoId}/tickets`),
    refetchInterval: 10_000, // tickets are edited outside the UI — keep the list fresh
  })
}

export function useTicket(repoId: number, slug: string | null) {
  return useQuery({
    queryKey: ['ticket', repoId, slug],
    queryFn: () => apiFetch<TicketDetail>(`/repos/${repoId}/tickets/${slug}`),
    enabled: slug !== null,
  })
}

export function useRepoRuns(repoId: number) {
  return useQuery({
    queryKey: ['runs', { repoId }],
    queryFn: () => apiFetch<Run[]>(`/runs?repo_id=${repoId}`),
    refetchInterval: 5_000,
  })
}

export function useCreateRun(repoId: number) {
  return useMutation({
    mutationFn: (body: RunInput) => apiPost<Run>('/runs', body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['runs', { repoId }] }),
  })
}

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

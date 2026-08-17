import type {
  AdoptInput,
  AuthoredStory,
  BoardPane,
  CoordinationClass,
  DecisionInput,
  Discussion,
  DiscussionDetail,
  EventInput,
  QueueName,
  Repo,
  RepoGateInput,
  Run,
  RunDetail,
  RunInput,
  StoryCreateInput,
  Ticket,
  TicketCreateInput,
  TicketDetail,
  WorkflowDocument,
  WorkflowProjection,
} from '@agentic-control-plane/domain-types'
import { useMutation, useQuery } from '@tanstack/react-query'
import { apiFetch, apiPost, apiPut } from './http'
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

export function useSetCloseGate(repoId: number) {
  return useMutation({
    mutationFn: (close_gate_command: string | null) => {
      const body: RepoGateInput = { close_gate_command }
      return apiPut<Repo>(`/repos/${repoId}/gate`, body)
    },
    onSuccess: (repo) => {
      queryClient.setQueryData(['repo', repoId], repo)
      queryClient.invalidateQueries({ queryKey: ['repos'] })
    },
  })
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

export function useWorkflow(repoId: number) {
  return useQuery({
    queryKey: ['workflow', repoId],
    queryFn: () => apiFetch<WorkflowProjection>(`/repos/${repoId}/workflow`),
    refetchInterval: 10_000,
  })
}

/** Read a work document by its current path — nested legacy files can share a
 * filename stem, so identity cannot name them. */
export function useWorkflowDocumentByPath(repoId: number, path: string | null) {
  return useQuery({
    queryKey: ['workflow-document-path', repoId, path],
    queryFn: () => apiFetch<WorkflowDocument>(
      `/repos/${repoId}/workflow/document?path=${encodeURIComponent(path ?? '')}`,
    ),
    enabled: path !== null,
  })
}

export function useWorkflowDocument(repoId: number, identity: string | null) {
  return useQuery({
    queryKey: ['workflow-document', repoId, identity],
    queryFn: () => apiFetch<WorkflowDocument>(
      `/repos/${repoId}/workflow/documents/${encodeURIComponent(identity ?? '')}`,
    ),
    enabled: identity !== null,
  })
}

export function useDiscussions(repoId: number) {
  return useQuery({
    queryKey: ['discussions', repoId],
    queryFn: () => apiFetch<Discussion[]>(`/repos/${repoId}/discussions`),
  })
}

export function useDiscussion(repoId: number, id: number | null) {
  return useQuery({
    queryKey: ['discussion', repoId, id],
    queryFn: () => apiFetch<DiscussionDetail>(`/repos/${repoId}/discussions/${id}`),
    enabled: id !== null,
  })
}

function cacheDiscussion(repoId: number, detail: DiscussionDetail) {
  queryClient.setQueryData(['discussion', repoId, detail.discussion.id], detail)
  queryClient.invalidateQueries({ queryKey: ['discussions', repoId] })
}

export function useStartDiscussion(repoId: number) {
  return useMutation({
    mutationFn: (message: string) =>
      apiPost<DiscussionDetail>(`/repos/${repoId}/discussions`, { message }),
    onSuccess: (d) => cacheDiscussion(repoId, d),
  })
}

export function useSendDiscussionMessage(repoId: number) {
  return useMutation({
    mutationFn: ({ id, message }: { id: number; message: string }) =>
      apiPost<DiscussionDetail>(`/repos/${repoId}/discussions/${id}/messages`, { message }),
    onSuccess: (d) => cacheDiscussion(repoId, d),
  })
}

export interface FreezeTarget {
  id: number
  slug?: string
  /** An epic to hang the story on, or `standalone` for no parent. Exactly one
   * of slug / epic_id / standalone. */
  epic_id?: string
  standalone?: boolean
  coordination_class?: CoordinationClass
}

export function useFreezeDiscussion(repoId: number) {
  return useMutation({
    mutationFn: ({ id, ...target }: FreezeTarget) =>
      apiPost<TicketDetail>(`/repos/${repoId}/discussions/${id}/freeze`, target),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets', repoId] })
      queryClient.invalidateQueries({ queryKey: ['discussions', repoId] })
      queryClient.invalidateQueries({ queryKey: ['workflow', repoId] })
    },
  })
}

export function useCreateStory(repoId: number) {
  return useMutation({
    mutationFn: (body: StoryCreateInput) =>
      apiPost<AuthoredStory>(`/repos/${repoId}/workflow/stories`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflow', repoId] }),
  })
}

export function useAdoptLegacy(repoId: number) {
  return useMutation({
    mutationFn: (body: AdoptInput) =>
      apiPost<AuthoredStory>(`/repos/${repoId}/workflow/stories/adopt`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflow', repoId] }),
  })
}

export function useMarkStoryReady(repoId: number) {
  return useMutation({
    mutationFn: (storyId: string) =>
      apiPost<AuthoredStory>(`/repos/${repoId}/workflow/stories/${storyId}/ready`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflow', repoId] }),
  })
}

export function useCreateTicket(repoId: number) {
  return useMutation({
    mutationFn: (body: TicketCreateInput) =>
      apiPost<TicketDetail>(`/repos/${repoId}/tickets`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tickets', repoId] }),
  })
}

export function useUpdateTicket(repoId: number) {
  return useMutation({
    mutationFn: ({ slug, content }: { slug: string; content: string }) =>
      apiPut<TicketDetail>(`/repos/${repoId}/tickets/${slug}`, { content }),
    onSuccess: (t) => {
      queryClient.invalidateQueries({ queryKey: ['tickets', repoId] })
      queryClient.invalidateQueries({ queryKey: ['ticket', repoId, t.slug] })
    },
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

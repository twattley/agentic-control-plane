// Add TanStack Query hooks here as you build features.
// Pattern:
//
//   export function useItems() {
//     return useQuery({ queryKey: ['items'], queryFn: () => apiFetch<Item[]>('/items') })
//   }
//
//   export function useCreateItem() {
//     return useMutation({
//       mutationFn: (body: CreateItemInput) => apiPost<Item>('/items', body),
//       onSuccess: () => queryClient.invalidateQueries({ queryKey: ['items'] }),
//     })
//   }

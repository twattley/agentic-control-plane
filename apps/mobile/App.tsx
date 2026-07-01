import { NavigationContainer } from '@react-navigation/native'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './src/api/queryClient'
import { RootNavigator } from './src/navigation'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <NavigationContainer>
        <RootNavigator />
      </NavigationContainer>
    </QueryClientProvider>
  )
}

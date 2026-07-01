import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { createNativeStackNavigator } from '@react-navigation/native-stack'
import { Text, View } from 'react-native'

export type RootStackParamList = {
  Tabs: undefined
}

const Stack = createNativeStackNavigator<RootStackParamList>()
const Tab = createBottomTabNavigator()

function PlaceholderScreen({ name }: { name: string }) {
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
      <Text>{name}</Text>
    </View>
  )
}

function TabNavigator() {
  return (
    <Tab.Navigator>
      <Tab.Screen name="Home" children={() => <PlaceholderScreen name="Home" />} />
    </Tab.Navigator>
  )
}

export function RootNavigator() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="Tabs" component={TabNavigator} options={{ headerShown: false }} />
    </Stack.Navigator>
  )
}

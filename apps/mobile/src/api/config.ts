import AsyncStorage from '@react-native-async-storage/async-storage'

const API_BASE_KEY = 'api_base_url'
const DEFAULT_API_BASE = 'http://localhost:8000/api/v1'

export async function getApiBase(): Promise<string> {
  const stored = await AsyncStorage.getItem(API_BASE_KEY)
  return stored ?? DEFAULT_API_BASE
}

export async function setApiBase(url: string): Promise<void> {
  await AsyncStorage.setItem(API_BASE_KEY, url)
}

export async function clearApiBase(): Promise<void> {
  await AsyncStorage.removeItem(API_BASE_KEY)
}

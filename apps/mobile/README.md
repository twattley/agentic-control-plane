# apps/mobile — Expo 54 + React Navigation

## Stack

- **Expo 54** + **React Native 0.76**
- **React Navigation v7** — bottom tabs + native stack
- **TanStack Query v5** — server state

## Source layout

```
src/
  api/
    config.ts     AsyncStorage URL management
    client.ts     apiFetch / apiPost / apiPut / apiDelete
    queryClient.ts
  navigation/
    index.tsx     RootNavigator (Stack + TabNavigator)
  features/       one folder per domain feature
    <name>/
      screens/
```

## Commands

```bash
make mobile   # start Expo dev server
```

Configure the API URL in the Settings tab on first launch.

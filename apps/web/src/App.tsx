import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ApiProvider } from './api/ApiProvider'
import { Inbox } from './features/runs/Inbox'
import { RunDetailPage } from './features/runs/RunDetail'

export default function App() {
  return (
    <ApiProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Inbox />} />
          <Route path="/runs/:id" element={<RunDetailPage />} />
        </Routes>
      </BrowserRouter>
    </ApiProvider>
  )
}

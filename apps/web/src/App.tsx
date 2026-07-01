import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ApiProvider } from './api/ApiProvider'
import { Projects } from './features/projects/Projects'
import { ProjectView } from './features/projects/ProjectView'
import { Inbox } from './features/runs/Inbox'
import { RunDetailPage } from './features/runs/RunDetail'

export default function App() {
  return (
    <ApiProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Projects />} />
          <Route path="/projects/:id" element={<ProjectView />} />
          <Route path="/inbox" element={<Inbox />} />
          <Route path="/runs/:id" element={<RunDetailPage />} />
        </Routes>
      </BrowserRouter>
    </ApiProvider>
  )
}

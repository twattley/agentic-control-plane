import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ApiProvider } from './api/ApiProvider'

function Home() {
  return <h1 className="text-2xl font-bold p-8">agentic-control-plane</h1>
}

export default function App() {
  return (
    <ApiProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </BrowserRouter>
    </ApiProvider>
  )
}

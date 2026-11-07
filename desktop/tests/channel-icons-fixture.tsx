// Isolated rendering entry: the actual page and stylesheet, synthetic API only.
import React from 'react'
import { createRoot } from 'react-dom/client'
import ChannelsPage from '../src/renderer/src/pages/ChannelsPage'
import '../src/renderer/src/index.css'

createRoot(document.getElementById('root')!).render(
  <div className="h-screen flex bg-base text-content">
    <ChannelsPage baseUrl={window.location.origin} />
  </div>
)

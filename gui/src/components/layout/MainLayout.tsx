import { ReactNode } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import DevConsole from '../DevConsole'
import { useDevStore, DEV_MODE_ENABLED } from '../../stores/devStore'

interface MainLayoutProps {
  children: ReactNode
}

export default function MainLayout({ children }: MainLayoutProps) {
  const devEnabled = useDevStore((state) => state.enabled)
  const devIsOpen = useDevStore((state) => state.isOpen)
  const showDevConsole = devEnabled || DEV_MODE_ENABLED

  return (
    <div className="flex h-screen bg-zinc-950">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main
          className="flex-1 overflow-auto p-6"
          style={{
            // Add padding for dev console when visible
            paddingBottom: showDevConsole ? (devIsOpen ? '26rem' : '3rem') : undefined,
          }}
        >
          {children}
        </main>
      </div>
      {showDevConsole && <DevConsole />}
    </div>
  )
}

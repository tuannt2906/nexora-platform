import { Navigate, Route, Routes } from 'react-router-dom';
import { useSession } from './api/context';
import { Layout } from './components/Layout';
import { TokenScreen } from './components/TokenScreen';
import { Adapters } from './pages/Adapters';
import { Audit } from './pages/Audit';
import { Connections } from './pages/Connections';
import { Modules } from './pages/Modules';
import { Overview } from './pages/Overview';

export function App() {
  const { token } = useSession();
  if (!token) return <TokenScreen />;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="modules" element={<Modules />} />
        <Route path="adapters" element={<Adapters />} />
        <Route path="connections" element={<Connections />} />
        <Route path="audit" element={<Audit />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

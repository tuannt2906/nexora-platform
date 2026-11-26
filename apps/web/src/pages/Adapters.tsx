import { useAdapters } from '../api/hooks';
import { MATURITY_HELP, MaturityBadge } from '../components/Badges';
import { QueryState } from '../components/QueryState';

export function Adapters() {
  const adapters = useAdapters();
  return (
    <>
      <h1>Engine adapters</h1>
      <div className="alert alert-warn" role="note">
        <strong>Read the maturity label.</strong> <MaturityBadge maturity="probe" /> means{' '}
        {MATURITY_HELP['probe']} Only <MaturityBadge maturity="functional" /> adapters have been
        verified against a real engine.
      </div>
      <QueryState query={adapters}>
        {(list) => (
          <table>
            <thead>
              <tr>
                <th scope="col">Engine</th>
                <th scope="col">Kind</th>
                <th scope="col">Maturity</th>
                <th scope="col">Capabilities</th>
                <th scope="col">Contract</th>
              </tr>
            </thead>
            <tbody>
              {list.map((a) => (
                <tr key={a.kind}>
                  <th scope="row">{a.display_name}</th>
                  <td>
                    <code>{a.kind}</code>
                  </td>
                  <td>
                    <MaturityBadge maturity={a.maturity} />
                  </td>
                  <td>{a.capabilities.join(', ') || '—'}</td>
                  <td>
                    <code>{a.contract_doc}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </QueryState>
    </>
  );
}

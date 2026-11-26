import { useAuditEvents } from '../api/hooks';
import { QueryState } from '../components/QueryState';

export function Audit() {
  const events = useAuditEvents();
  return (
    <>
      <h1>Audit log</h1>
      <QueryState query={events}>
        {(list) =>
          list.length === 0 ? (
            <p className="muted">No audit events recorded yet.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th scope="col">When (UTC)</th>
                  <th scope="col">Actor</th>
                  <th scope="col">Action</th>
                  <th scope="col">Target</th>
                  <th scope="col">Detail</th>
                </tr>
              </thead>
              <tbody>
                {list.map((e) => (
                  <tr key={`${e.occurred_at}-${e.action}-${e.target}`}>
                    <td>
                      <time dateTime={e.occurred_at}>{e.occurred_at}</time>
                    </td>
                    <td>{e.actor}</td>
                    <td>
                      <code>{e.action}</code>
                    </td>
                    <td>{e.target}</td>
                    <td>
                      <code>{JSON.stringify(e.detail)}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        }
      </QueryState>
    </>
  );
}

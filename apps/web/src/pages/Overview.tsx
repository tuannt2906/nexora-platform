import { useAdapters, useConnectionsHealth, useModules, usePlatform } from '../api/hooks';
import type { ConnectionHealth, HealthState } from '../api/types';
import { MaturityBadge } from '../components/Badges';
import { QueryState } from '../components/QueryState';

const STATES: HealthState[] = ['healthy', 'degraded', 'unhealthy', 'unknown'];

function countBy<T>(items: T[], key: (item: T) => string): Record<string, number> {
  const out: Record<string, number> = {};
  for (const item of items) out[key(item)] = (out[key(item)] ?? 0) + 1;
  return out;
}

function HealthSummary({ items }: { items: ConnectionHealth[] }) {
  if (items.length === 0) return <p className="muted">No engine connections registered yet.</p>;
  const counts = countBy(items, (i) => i.health.state);
  return (
    <ul className="stat-row">
      {STATES.map((s) => (
        <li key={s}>
          <span className="stat">{counts[s] ?? 0}</span> {s}
        </li>
      ))}
    </ul>
  );
}

export function Overview() {
  const platform = usePlatform();
  const modules = useModules();
  const adapters = useAdapters();
  const health = useConnectionsHealth();

  return (
    <>
      <h1>Overview</h1>
      <section aria-labelledby="ov-platform" className="card">
        <h2 id="ov-platform">Platform</h2>
        <QueryState query={platform}>
          {(p) => (
            <dl className="kv">
              <dt>Service</dt>
              <dd>{p.name}</dd>
              <dt>Version</dt>
              <dd>{p.version}</dd>
              <dt>Environment</dt>
              <dd>{p.environment}</dd>
              <dt>Build</dt>
              <dd>
                <code>{p.git_sha}</code>
              </dd>
            </dl>
          )}
        </QueryState>
      </section>

      <div className="grid">
        <section aria-labelledby="ov-modules" className="card">
          <h2 id="ov-modules">Domain modules</h2>
          <QueryState query={modules}>
            {(list) => {
              const byMaturity = countBy(list, (m) => m.maturity);
              return (
                <>
                  <p>
                    <span className="stat">{list.length}</span> modules
                  </p>
                  <ul className="chips">
                    {Object.entries(byMaturity).map(([m, n]) => (
                      <li key={m}>
                        <MaturityBadge maturity={m} /> × {n}
                      </li>
                    ))}
                  </ul>
                </>
              );
            }}
          </QueryState>
        </section>

        <section aria-labelledby="ov-adapters" className="card">
          <h2 id="ov-adapters">Engine adapters</h2>
          <QueryState query={adapters}>
            {(list) => {
              const byMaturity = countBy(list, (a) => a.maturity);
              return (
                <>
                  <p>
                    <span className="stat">{list.length}</span> adapters
                  </p>
                  <ul className="chips">
                    {Object.entries(byMaturity).map(([m, n]) => (
                      <li key={m}>
                        <MaturityBadge maturity={m} /> × {n}
                      </li>
                    ))}
                  </ul>
                </>
              );
            }}
          </QueryState>
        </section>

        <section aria-labelledby="ov-health" className="card">
          <h2 id="ov-health">Connection health</h2>
          <QueryState query={health}>{(items) => <HealthSummary items={items} />}</QueryState>
        </section>
      </div>
    </>
  );
}

import { useModules } from '../api/hooks';
import type { ModuleSpec } from '../api/types';
import { MaturityBadge } from '../components/Badges';
import { QueryState } from '../components/QueryState';

function progress(module: ModuleSpec) {
  const count = { met: 0, unmet: 0, planned: 0 };
  for (const c of module.acceptance) count[c.status] += 1;
  return count;
}

function ModuleCard({ module }: { module: ModuleSpec }) {
  const p = progress(module);
  const total = module.acceptance.length;
  return (
    <li className="card module">
      <details>
        <summary>
          <span className="module-title">{module.title}</span>
          <MaturityBadge maturity={module.maturity} />
          <span className="muted">
            {p.met}/{total} criteria met
          </span>
        </summary>
        <p>{module.summary}</p>

        <div
          className="progress"
          role="img"
          aria-label={`${p.met.toString()} met, ${p.unmet.toString()} unmet, ${p.planned.toString()} planned`}
        >
          <span className="seg seg-met" style={{ flexGrow: p.met }} />
          <span className="seg seg-unmet" style={{ flexGrow: p.unmet }} />
          <span className="seg seg-planned" style={{ flexGrow: p.planned }} />
        </div>
        <p className="muted small">
          {p.met} met · {p.unmet} unmet · {p.planned} planned
        </p>

        <h3>Responsibilities</h3>
        <ul>
          {module.responsibilities.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>

        <h3>Public interfaces</h3>
        <ul>
          {module.public_interfaces.map((i) => (
            <li key={i}>
              <code>{i}</code>
            </li>
          ))}
        </ul>

        {module.engines.length > 0 ? (
          <>
            <h3>Engines</h3>
            <ul className="chips">
              {module.engines.map((e) => (
                <li key={e} className="chip">
                  {e}
                </li>
              ))}
            </ul>
          </>
        ) : null}

        <h3>Acceptance criteria</h3>
        <table>
          <thead>
            <tr>
              <th scope="col">ID</th>
              <th scope="col">Criterion</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {module.acceptance.map((c) => (
              <tr key={c.id}>
                <td>{c.id}</td>
                <td>{c.criterion}</td>
                <td>
                  <span className={`badge badge-crit-${c.status}`}>{c.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </li>
  );
}

export function Modules() {
  const modules = useModules();
  return (
    <>
      <h1>Domain modules</h1>
      <p className="muted">
        Status is derived from each module&apos;s <code>module.toml</code>. A criterion is{' '}
        <em>met</em> only when a passing test is its evidence.
      </p>
      <QueryState query={modules}>
        {(list) => (
          <ul className="list">
            {list.map((m) => (
              <ModuleCard key={m.id} module={m} />
            ))}
          </ul>
        )}
      </QueryState>
    </>
  );
}

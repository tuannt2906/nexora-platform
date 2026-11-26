import { useState, type SubmitEvent } from 'react';
import {
  useConnections,
  useConnectionsHealth,
  useCreateConnection,
  useDeleteConnection,
} from '../api/hooks';
import { ENGINE_KINDS, type ConnectionCreate, type EngineKind } from '../api/types';
import { HealthBadge, MaturityBadge } from '../components/Badges';
import { QueryState, errorMessage } from '../components/QueryState';
import { validateConnection, type FormErrors } from './validation';

function CreateForm() {
  const create = useCreateConnection();
  const [kind, setKind] = useState<EngineKind>('trino');
  const [name, setName] = useState('');
  const [endpoint, setEndpoint] = useState('');
  const [secretRef, setSecretRef] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});

  function submit(event: SubmitEvent) {
    event.preventDefault();
    const found = validateConnection({ name, endpoint, secretRef });
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    const body: ConnectionCreate = { kind, name: name.trim(), endpoint: endpoint.trim() };
    if (secretRef.trim() !== '') body.secret_ref = secretRef.trim();
    create.mutate(body, {
      onSuccess: () => {
        setName('');
        setEndpoint('');
        setSecretRef('');
      },
    });
  }

  return (
    <form onSubmit={submit} className="card form" aria-labelledby="new-conn" noValidate>
      <h2 id="new-conn">Register engine connection</h2>

      <label htmlFor="kind">Engine kind</label>
      <select
        id="kind"
        value={kind}
        onChange={(e) => {
          setKind(e.target.value as EngineKind);
        }}
      >
        {ENGINE_KINDS.map((k) => (
          <option key={k} value={k}>
            {k}
          </option>
        ))}
      </select>

      <label htmlFor="name">Name</label>
      <input
        id="name"
        value={name}
        aria-invalid={errors.name ? true : undefined}
        aria-describedby={errors.name ? 'name-err' : undefined}
        onChange={(e) => {
          setName(e.target.value);
        }}
      />
      {errors.name ? (
        <p id="name-err" className="field-error">
          {errors.name}
        </p>
      ) : null}

      <label htmlFor="endpoint">Endpoint</label>
      <input
        id="endpoint"
        value={endpoint}
        placeholder="http://trino.data.svc:8080"
        aria-invalid={errors.endpoint ? true : undefined}
        aria-describedby={errors.endpoint ? 'endpoint-err' : undefined}
        onChange={(e) => {
          setEndpoint(e.target.value);
        }}
      />
      {errors.endpoint ? (
        <p id="endpoint-err" className="field-error">
          {errors.endpoint}
        </p>
      ) : null}

      <label htmlFor="secret_ref">Secret reference (optional)</label>
      <input
        id="secret_ref"
        value={secretRef}
        placeholder="k8s://nexora/trino-credentials"
        aria-describedby="secret-help"
        onChange={(e) => {
          setSecretRef(e.target.value);
        }}
      />
      <p id="secret-help" className="muted small">
        This is a <strong>reference</strong> to a secret held in your external secret manager —
        never paste a password or token here.
      </p>

      {create.isError ? (
        <p role="alert" className="alert alert-error">
          {errorMessage(create.error)}
        </p>
      ) : null}
      {create.isSuccess ? (
        <p role="status" className="alert alert-ok">
          Connection registered.
        </p>
      ) : null}
      <button type="submit" className="primary" disabled={create.isPending}>
        {create.isPending ? 'Saving…' : 'Register connection'}
      </button>
    </form>
  );
}

function DeleteButton({ name }: { name: string }) {
  const del = useDeleteConnection();
  const [confirming, setConfirming] = useState(false);
  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => {
          setConfirming(true);
        }}
        aria-label={`Delete ${name}`}
      >
        Delete
      </button>
    );
  }
  return (
    <span className="confirm">
      <button
        type="button"
        className="danger"
        disabled={del.isPending}
        onClick={() => {
          del.mutate(name);
        }}
        aria-label={`Confirm delete ${name}`}
      >
        Confirm
      </button>
      <button
        type="button"
        onClick={() => {
          setConfirming(false);
        }}
      >
        Cancel
      </button>
      {del.isError ? <span role="alert">{errorMessage(del.error)}</span> : null}
    </span>
  );
}

export function Connections() {
  const connections = useConnections();
  const health = useConnectionsHealth();
  const healthByName = new Map((health.data ?? []).map((h) => [h.name, h]));

  return (
    <>
      <h1>Engine connections</h1>
      <CreateForm />
      <h2>Registered connections</h2>
      <QueryState query={connections}>
        {(list) =>
          list.length === 0 ? (
            <p className="muted">No connections registered yet.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Kind</th>
                  <th scope="col">Endpoint</th>
                  <th scope="col">Health</th>
                  <th scope="col">Adapter maturity</th>
                  <th scope="col">
                    <span className="visually-hidden">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {list.map((c) => {
                  const h = healthByName.get(c.name);
                  return (
                    <tr key={c.name}>
                      <th scope="row">{c.name}</th>
                      <td>
                        <code>{c.kind}</code>
                      </td>
                      <td>
                        <code>{c.endpoint}</code>
                      </td>
                      <td>
                        {h ? (
                          <>
                            <HealthBadge state={h.health.state} />{' '}
                            <span className="muted small">{h.health.detail}</span>
                          </>
                        ) : health.isError ? (
                          <span className="muted">unavailable</span>
                        ) : (
                          <span className="muted">checking…</span>
                        )}
                      </td>
                      <td>{h ? <MaturityBadge maturity={h.maturity} /> : '—'}</td>
                      <td>
                        <DeleteButton name={c.name} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )
        }
      </QueryState>
    </>
  );
}

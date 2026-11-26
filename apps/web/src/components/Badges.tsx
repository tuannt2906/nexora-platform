import type { HealthState } from '../api/types';

/** Plain-language meaning of each maturity level. "probe" is deliberately NOT "functional". */
export const MATURITY_HELP: Record<string, string> = {
  planned: 'Nothing implemented yet.',
  contract: 'Interface + in-memory fake + contract tests. No real engine involved.',
  probe:
    'Health/capability probe only, verified against a mocked protocol. NOT verified against a live engine and does not run queries or jobs.',
  functional: 'Implements the domain interface and is verified against a real engine in CI.',
  production: 'Functional and operated/observed in a production environment.',
};

export function MaturityBadge({ maturity }: { maturity: string }) {
  return (
    <span
      className={`badge badge-maturity badge-${maturity}`}
      title={MATURITY_HELP[maturity] ?? maturity}
    >
      {maturity}
    </span>
  );
}

export function HealthBadge({ state }: { state: HealthState }) {
  return <span className={`badge badge-health badge-${state}`}>{state}</span>;
}

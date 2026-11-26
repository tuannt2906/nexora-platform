import type { components } from './schema';

type S = components['schemas'];

export type PlatformInfo = S['PlatformInfo'];
export type ModuleSpec = S['ModuleSpec'];
export type AcceptanceCriterion = S['AcceptanceCriterion'];
export type AdapterInfo = S['AdapterInfo'];
export type ConnectionOut = S['ConnectionOut'];
export type ConnectionCreate = S['ConnectionCreate'];
export type ConnectionHealth = S['ConnectionHealth'];
export type AuditEvent = S['AuditEventOut'];
export type EngineKind = S['EngineKind'];
export type HealthState = S['HealthState'];
export type Maturity = S['Maturity'];
export type CriterionStatus = S['CriterionStatus'];

/** Runtime list of engine kinds; the compile-time check below fails if the API adds a value. */
export const ENGINE_KINDS = [
  'kafka',
  'kafka-connect',
  'flink',
  'spark',
  'iceberg-rest-catalog',
  'object-store-s3',
  'trino',
  'airflow',
  'openlineage',
  'prometheus',
] as const satisfies readonly EngineKind[];

type MissingKinds = Exclude<EngineKind, (typeof ENGINE_KINDS)[number]>;
export const allEngineKindsListed: MissingKinds extends never ? true : never = true;

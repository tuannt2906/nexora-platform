/** Client-side mirror of the API validation (the server remains authoritative). */
export const NAME_PATTERN = /^[a-z0-9]([-a-z0-9]*[a-z0-9])?$/;
const HOSTPORT = /^[A-Za-z0-9.-]+(:\d{1,5})?(,[A-Za-z0-9.-]+(:\d{1,5})?)*$/;

export interface ConnectionFormValues {
  name: string;
  endpoint: string;
  secretRef: string;
}

export type FormErrors = Partial<Record<keyof ConnectionFormValues, string>>;

export function validateConnection(values: ConnectionFormValues): FormErrors {
  const errors: FormErrors = {};
  const name = values.name.trim();
  if (name === '') errors.name = 'Name is required.';
  else if (name.length > 63) errors.name = 'Name must be at most 63 characters.';
  else if (!NAME_PATTERN.test(name))
    errors.name =
      'Use lowercase letters, digits and hyphens; start and end with a letter or digit.';

  const endpoint = values.endpoint.trim();
  if (endpoint === '') errors.endpoint = 'Endpoint is required.';
  else if (endpoint.includes('://')) {
    if (!/^https?:\/\//i.test(endpoint))
      errors.endpoint = 'Only http:// and https:// URLs are allowed.';
  } else if (!HOSTPORT.test(endpoint)) {
    errors.endpoint = 'Use host[:port] or an http(s) URL.';
  }

  if (values.secretRef.length > 512) errors.secretRef = 'Reference is too long.';
  return errors;
}

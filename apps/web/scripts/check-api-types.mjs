// Fails (exit 1) when src/api/schema.d.ts differs from what the committed OpenAPI contract generates.
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const spec = resolve(root, '../../contracts/openapi/control-plane.v1.json');
const committed = resolve(root, 'src/api/schema.d.ts');
const bin = resolve(root, 'node_modules/openapi-typescript/bin/cli.js');

const dir = mkdtempSync(join(tmpdir(), 'nexora-api-'));
const generated = join(dir, 'schema.d.ts');
try {
  execFileSync(process.execPath, [bin, spec, '-o', generated], { stdio: 'ignore' });
  const norm = (p) => readFileSync(p, 'utf8').replaceAll('\r\n', '\n');
  if (norm(generated) !== norm(committed)) {
    console.error(
      'API types are out of date. Run: npm run gen:api (in apps/web) and commit the result.',
    );
    process.exit(1);
  }
  console.log('API types match contracts/openapi/control-plane.v1.json');
} finally {
  rmSync(dir, { recursive: true, force: true });
}

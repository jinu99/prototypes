import { readFile } from 'fs/promises';
import { join } from 'path';

/**
 * Extract project metadata from package.json or pyproject.toml
 */
export async function extractMetadata(projectDir) {
  const meta = {
    name: '',
    description: '',
    version: '',
    license: '',
    author: '',
    homepage: '',
    repository: '',
  };

  // Try package.json first
  try {
    const raw = await readFile(join(projectDir, 'package.json'), 'utf-8');
    const pkg = JSON.parse(raw);
    meta.name = pkg.name || '';
    meta.description = pkg.description || '';
    meta.version = pkg.version || '';
    meta.license = pkg.license || '';
    meta.author = typeof pkg.author === 'string' ? pkg.author : (pkg.author?.name || '');
    meta.homepage = pkg.homepage || '';
    meta.repository = typeof pkg.repository === 'string' ? pkg.repository : (pkg.repository?.url || '');
    return meta;
  } catch {}

  // Try pyproject.toml
  try {
    const raw = await readFile(join(projectDir, 'pyproject.toml'), 'utf-8');
    meta.name = extractToml(raw, 'name') || '';
    meta.description = extractToml(raw, 'description') || '';
    meta.version = extractToml(raw, 'version') || '';
    meta.license = extractToml(raw, 'license') || '';
    const authors = raw.match(/authors\s*=\s*\[([^\]]*)\]/);
    if (authors) {
      const nameMatch = authors[1].match(/name\s*=\s*"([^"]*)"/);
      meta.author = nameMatch ? nameMatch[1] : '';
    }
    return meta;
  } catch {}

  return meta;
}

function extractToml(content, key) {
  const match = content.match(new RegExp(`^${key}\\s*=\\s*"([^"]*)"`, 'm'));
  return match ? match[1] : '';
}

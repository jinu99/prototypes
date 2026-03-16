import { readFile, writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { parseReadme } from './parser.js';
import { extractMetadata } from './metadata.js';
import { generateChangelog } from './changelog.js';
import { generateLaunchPosts } from './launch-posts.js';
import { renderLanding, renderChangelog } from './templates.js';

export async function build(projectDir, options = {}) {
  const outDir = join(projectDir, options.outDir || 'dist');
  const theme = options.theme || 'minimal';

  await mkdir(outDir, { recursive: true });

  // 1. Read and parse README
  let readmeContent;
  try {
    readmeContent = await readFile(join(projectDir, 'README.md'), 'utf-8');
  } catch {
    throw new Error('README.md not found in ' + projectDir);
  }

  const sections = parseReadme(readmeContent);
  console.log(`  ✓ Parsed README.md → hero: "${sections.hero.title}", ${sections.features.length} feature sections, ${sections.install.length} install sections`);

  // 2. Extract metadata
  const meta = await extractMetadata(projectDir);
  if (!meta.name && sections.hero.title) {
    meta.name = sections.hero.title;
  }
  console.log(`  ✓ Metadata: ${meta.name} v${meta.version || '?'}`);

  // 3. Generate landing page
  // Extract badge images from hero, separate from text content
  const heroBadges = extractBadges(sections.hero.description);
  const landingHtml = renderLanding({ ...sections, heroBadges, meta }, theme);
  const landingPath = join(outDir, 'index.html');
  await writeFile(landingPath, landingHtml, 'utf-8');
  console.log(`  ✓ Landing page → ${landingPath} (theme: ${theme})`);

  // 4. Generate changelog
  const changelog = await generateChangelog(projectDir);
  const changelogHtml = renderChangelog(meta, changelog.html, theme);
  const changelogPath = join(outDir, 'changelog.html');
  await writeFile(changelogPath, changelogHtml, 'utf-8');
  console.log(`  ✓ Changelog → ${changelogPath} (${changelog.entries.length} commits)`);

  // 5. Generate launch posts
  const posts = generateLaunchPosts(meta, sections);
  const postsDir = join(outDir, 'launch-posts');
  await mkdir(postsDir, { recursive: true });

  await writeFile(join(postsDir, 'product-hunt.md'), posts.productHunt, 'utf-8');
  await writeFile(join(postsDir, 'reddit.md'), posts.reddit, 'utf-8');
  await writeFile(join(postsDir, 'hacker-news.md'), posts.hackerNews, 'utf-8');
  console.log(`  ✓ Launch posts → ${postsDir}/`);

  return { outDir, landingPath, changelogPath, postsDir, sections, meta };
}

function extractBadges(html) {
  if (!html) return '';
  // Find paragraphs that contain only images (badges)
  const badgePattern = /<p>(?:\s*<a[^>]*><img[^>]*\/><\/a>\s*)+<\/p>/g;
  const matches = html.match(badgePattern);
  return matches ? matches.join('\n') : '';
}

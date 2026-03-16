#!/usr/bin/env node

import { Command } from 'commander';
import { writeFile } from 'fs/promises';
import { join, resolve } from 'path';
import { build } from '../src/builder.js';
import { AVAILABLE_THEMES } from '../src/templates.js';

const program = new Command();

program
  .name('indie-launch-kit')
  .description('Generate landing pages, changelogs, and launch posts from your README')
  .version('1.0.0');

program
  .command('init')
  .description('Create a config file in the current directory')
  .action(async () => {
    const config = {
      theme: 'minimal',
      outDir: 'dist',
    };
    const configPath = join(process.cwd(), '.launchkit.json');
    await writeFile(configPath, JSON.stringify(config, null, 2) + '\n', 'utf-8');
    console.log('Created .launchkit.json');
    console.log('Available themes:', AVAILABLE_THEMES.join(', '));
    console.log('\nRun `npx indie-launch-kit build` to generate your landing page.');
  });

program
  .command('build')
  .description('Build landing page, changelog, and launch posts')
  .option('-d, --dir <path>', 'Project directory', process.cwd())
  .option('-t, --theme <theme>', `Theme (${AVAILABLE_THEMES.join(', ')})`, 'minimal')
  .option('-o, --out <dir>', 'Output directory', 'dist')
  .action(async (opts) => {
    const projectDir = resolve(opts.dir);
    console.log(`\n🚀 indie-launch-kit build`);
    console.log(`  Project: ${projectDir}`);
    console.log(`  Theme: ${opts.theme}`);
    console.log('');

    if (!AVAILABLE_THEMES.includes(opts.theme)) {
      console.error(`Error: Unknown theme "${opts.theme}". Available: ${AVAILABLE_THEMES.join(', ')}`);
      process.exit(1);
    }

    try {
      const result = await build(projectDir, {
        theme: opts.theme,
        outDir: opts.out,
      });
      console.log(`\n✅ Done! Open ${result.landingPath} in your browser.`);
    } catch (err) {
      console.error(`\n❌ Error: ${err.message}`);
      process.exit(1);
    }
  });

program.parse();

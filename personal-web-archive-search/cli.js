#!/usr/bin/env node
const { openDb, initDb, addPage, search, listPages, getPageCount } = require('./db');
const { extractFromUrl } = require('./extractor');

async function main() {
  const db = openDb();
  initDb(db);

  const [,, command, ...args] = process.argv;

  switch (command) {
    case 'add': {
      const url = args[0];
      if (!url) {
        console.error('Usage: node cli.js add <url>');
        process.exit(1);
      }
      console.log(`Fetching: ${url}`);
      try {
        const article = await extractFromUrl(url);
        addPage(db, article);
        console.log(`✓ Added: "${article.title}" (${article.lang}, ${article.content.length} chars)`);
      } catch (err) {
        console.error(`✗ Failed: ${err.message}`);
        process.exit(1);
      }
      break;
    }

    case 'search': {
      const query = args.join(' ');
      if (!query) {
        console.error('Usage: node cli.js search <query>');
        process.exit(1);
      }
      const results = search(db, query);
      if (results.length === 0) {
        console.log('No results found.');
      } else {
        console.log(`Found ${results.length} result(s):\n`);
        for (const r of results) {
          console.log(`  ${r.title}`);
          console.log(`  ${r.url}`);
          const plain = r.snippet.replace(/<\/?mark>/g, '');
          console.log(`  …${plain.substring(0, 120)}…`);
          console.log();
        }
      }
      break;
    }

    case 'list': {
      const pages = listPages(db);
      if (pages.length === 0) {
        console.log('No pages archived yet.');
      } else {
        console.log(`${pages.length} page(s) archived:\n`);
        for (const p of pages) {
          console.log(`  [${p.id}] ${p.title}`);
          console.log(`      ${p.url} (${p.added_at})`);
        }
      }
      break;
    }

    case 'stats': {
      const count = getPageCount(db);
      console.log(`Total pages: ${count}`);
      break;
    }

    default:
      console.log(`Personal Web Archive Search

Usage:
  node cli.js add <url>       Add a URL to the archive
  node cli.js search <query>  Search the archive
  node cli.js list            List all archived pages
  node cli.js stats           Show archive statistics`);
  }

  db.close();
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});

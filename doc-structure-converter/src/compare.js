import { readFileSync, writeFileSync } from "node:fs";
import { join, dirname, basename } from "node:path";
import { analyzeDocument } from "./parser.js";
import { astToTypst } from "./typst-gen.js";
import { renderTypstToPdf, renderPandocPdf } from "./renderer.js";

export function runComparison(inputPath, outputDir) {
  const markdown = readFileSync(inputPath, "utf-8");
  const name = basename(inputPath, ".md");

  console.log(`\n=== Before/After Comparison: ${name} ===\n`);

  // Analyze document
  const { blocks, stats } = analyzeDocument(markdown);
  console.log("Document stats:");
  console.log(`  Blocks: ${stats.total}`);
  console.log(`  Tables: ${stats.tables}`);
  console.log(`  Code blocks: ${stats.codeBlocks}`);
  console.log(`  Lists: ${stats.lists}`);
  console.log(`  Unbreakable blocks: ${stats.unbreakable}`);

  // 1. Pandoc baseline (before)
  const pandocOut = join(outputDir, `${name}-pandoc.pdf`);
  console.log(`\n[BEFORE] Pandoc default → ${pandocOut}`);
  const pandocResult = renderPandocPdf(inputPath, pandocOut);
  if (pandocResult.success) {
    console.log("  ✓ Pandoc PDF generated");
  } else {
    console.log(`  ✗ Pandoc failed: ${pandocResult.error}`);
  }

  // 2. Our tool (after) — with breakable hints
  const typstContent = astToTypst(blocks);
  const typstDebug = join(outputDir, `${name}-docconv.typ`);
  writeFileSync(typstDebug, typstContent, "utf-8");
  console.log(`  [debug] Typst source → ${typstDebug}`);

  const ourOut = join(outputDir, `${name}-docconv.pdf`);
  console.log(`\n[AFTER] docconv (structure-aware) → ${ourOut}`);
  const ourResult = renderTypstToPdf(typstContent, ourOut);
  if (ourResult.success) {
    console.log("  ✓ docconv PDF generated");
  } else {
    console.log(`  ✗ docconv failed: ${ourResult.error}`);
  }

  console.log(`\n=== Compare the two PDFs ===`);
  console.log(`  Pandoc (baseline): ${pandocOut}`);
  console.log(`  docconv (ours):    ${ourOut}`);
  console.log(
    `  Look for: tables/code blocks split across pages in Pandoc but not in docconv\n`
  );

  return { pandocResult, ourResult, stats };
}

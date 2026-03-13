#!/usr/bin/env node

import { Command } from "commander";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve, dirname, basename, join } from "node:path";
import { analyzeDocument } from "./parser.js";
import { astToTypst } from "./typst-gen.js";
import { renderTypstToPdf } from "./renderer.js";
import { runComparison } from "./compare.js";

const program = new Command();

program
  .name("docconv")
  .description(
    "Structure-aware Markdown to PDF converter using AST block boundary analysis"
  )
  .version("0.1.0");

program
  .command("convert")
  .description("Convert Markdown to PDF with smart page breaks")
  .argument("<input>", "Input Markdown file")
  .option("-o, --output <path>", "Output PDF path")
  .option("--debug", "Save intermediate Typst file")
  .action((input, opts) => {
    const inputPath = resolve(input);
    const markdown = readFileSync(inputPath, "utf-8");

    const outputPath =
      opts.output || inputPath.replace(/\.md$/, ".pdf") || input + ".pdf";

    console.log(`Converting: ${inputPath}`);

    // Parse and analyze
    const { blocks, stats } = analyzeDocument(markdown);
    console.log(
      `  Parsed ${stats.total} blocks (${stats.unbreakable} unbreakable)`
    );

    // Generate Typst
    const typstContent = astToTypst(blocks);

    if (opts.debug) {
      const debugPath = outputPath.replace(/\.pdf$/, ".typ");
      writeFileSync(debugPath, typstContent, "utf-8");
      console.log(`  Debug Typst saved: ${debugPath}`);
    }

    // Render PDF
    const result = renderTypstToPdf(typstContent, resolve(outputPath));
    if (result.success) {
      console.log(`  ✓ PDF saved: ${result.outputPath}`);
    } else {
      console.error(`  ✗ Failed: ${result.error}`);
      process.exit(1);
    }
  });

program
  .command("compare")
  .description("Generate before/after comparison with Pandoc")
  .argument("<input>", "Input Markdown file")
  .option("-d, --output-dir <dir>", "Output directory", "./output")
  .action((input, opts) => {
    const inputPath = resolve(input);
    const outputDir = resolve(opts.outputDir);
    runComparison(inputPath, outputDir);
  });

program
  .command("analyze")
  .description("Analyze Markdown structure without converting")
  .argument("<input>", "Input Markdown file")
  .action((input) => {
    const inputPath = resolve(input);
    const markdown = readFileSync(inputPath, "utf-8");
    const { blocks, stats } = analyzeDocument(markdown);

    console.log(`\nDocument Analysis: ${inputPath}\n`);
    console.log(`Total blocks: ${stats.total}`);
    console.log(`  Headings:    ${stats.headings}`);
    console.log(`  Tables:      ${stats.tables}`);
    console.log(`  Code blocks: ${stats.codeBlocks}`);
    console.log(`  Lists:       ${stats.lists}`);
    console.log(`  Images:      ${stats.images}`);
    console.log(`  Unbreakable: ${stats.unbreakable}`);
    console.log(`\nBlock sequence:`);
    blocks.forEach((b, i) => {
      const flag = b.breakable ? "  " : "🔒";
      console.log(`  ${i + 1}. ${flag} ${b.type}`);
    });
  });

program.parse();

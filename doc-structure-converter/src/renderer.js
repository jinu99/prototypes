import { writeFileSync, unlinkSync, existsSync, mkdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join, dirname } from "node:path";
import { tmpdir } from "node:os";

const TYPST_BIN =
  process.env.TYPST_BIN || join(process.env.HOME, ".local/bin/typst");
const PANDOC_BIN =
  process.env.PANDOC_BIN || join(process.env.HOME, ".local/bin/pandoc");

export function renderTypstToPdf(typstContent, outputPath) {
  const tmpTypst = join(tmpdir(), `docconv-${Date.now()}.typ`);

  try {
    const outDir = dirname(outputPath);
    if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });

    writeFileSync(tmpTypst, typstContent, "utf-8");
    execFileSync(TYPST_BIN, ["compile", tmpTypst, outputPath], {
      stdio: "pipe",
    });
    return { success: true, outputPath };
  } catch (err) {
    return { success: false, error: err.stderr?.toString() || err.message };
  } finally {
    if (existsSync(tmpTypst)) unlinkSync(tmpTypst);
  }
}

export function renderPandocPdf(markdownPath, outputPath) {
  try {
    const outDir = dirname(outputPath);
    if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });

    execFileSync(
      PANDOC_BIN,
      [
        markdownPath,
        "-o",
        outputPath,
        `--pdf-engine=${TYPST_BIN}`,
        "-V",
        "mainfont=New Computer Modern",
      ],
      { stdio: "pipe" }
    );
    return { success: true, outputPath };
  } catch (err) {
    return { success: false, error: err.stderr?.toString() || err.message };
  }
}

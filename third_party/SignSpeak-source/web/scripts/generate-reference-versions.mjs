import { createHash } from "node:crypto";
import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const referenceDir = path.join(root, "public", "assets", "reference");
const outputPath = path.join(root, "src", "generated", "referenceImageVersions.ts");

const files = (await readdir(referenceDir))
  .filter((name) => /^[A-Z]_test\.jpg$/.test(name))
  .sort();

const versions = {};

for (const file of files) {
  const letter = file[0];
  const buffer = await readFile(path.join(referenceDir, file));
  versions[letter] = createHash("sha256").update(buffer).digest("hex").slice(0, 16);
}

const body = `export const REFERENCE_IMAGE_VERSIONS: Record<string, string> = ${JSON.stringify(
  versions,
  null,
  2,
)};\n`;

await mkdir(path.dirname(outputPath), { recursive: true });
await writeFile(outputPath, body, "utf8");

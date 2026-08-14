import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const frontendRoot = resolve(import.meta.dirname, "..");
const repositoryRoot = resolve(frontendRoot, "..");
const temporaryDirectory = mkdtempSync(join(tmpdir(), "opsmind-openapi-"));

try {
  const temporaryOpenApi = join(temporaryDirectory, "openapi.json");
  const temporarySchema = join(temporaryDirectory, "schema.ts");

  execFileSync(
    "uv",
    [
      "run",
      "--project",
      repositoryRoot,
      "python",
      join(repositoryRoot, "scripts", "export_openapi.py"),
      "--output",
      temporaryOpenApi,
    ],
    { cwd: frontendRoot, stdio: "inherit" },
  );
  execFileSync(
    resolve(frontendRoot, "node_modules", ".bin", "openapi-typescript"),
    [temporaryOpenApi, "-o", temporarySchema],
    { cwd: frontendRoot, stdio: "inherit" },
  );

  const comparisons = [
    [join(frontendRoot, "openapi", "openapi.json"), temporaryOpenApi],
    [join(frontendRoot, "src", "api", "generated", "schema.ts"), temporarySchema],
  ];

  for (const [checkedInPath, generatedPath] of comparisons) {
    if (readFileSync(checkedInPath, "utf8") !== readFileSync(generatedPath, "utf8")) {
      throw new Error(
        `${checkedInPath} is stale; run npm run openapi:generate from frontend/`,
      );
    }
  }

  process.stdout.write("OpenAPI contract is current and reproducible.\n");
} finally {
  rmSync(temporaryDirectory, { force: true, recursive: true });
}

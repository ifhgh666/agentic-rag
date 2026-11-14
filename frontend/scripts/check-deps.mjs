import { readFile, readdir } from "node:fs/promises";
import { resolve, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const rootIndex = process.argv.indexOf("--root");
const root = rootIndex < 0 ? resolve(dirname(fileURLToPath(import.meta.url)), "..") : resolve(process.argv[rootIndex + 1]);
const readJson = async (name) => JSON.parse(await readFile(resolve(root, name), "utf8"));
const [pkg, lock, policy] = await Promise.all([readJson("package.json"), readJson("package-lock.json"), readJson("dependency-policy.json")]);
const issues = [];
if (Number(process.versions.node.split(".")[0]) < 22) issues.push("Node >=22 is required by cn");
for (const [section, allowed] of [["dependencies", Object.keys(policy.runtime)], ["devDependencies", policy.development]]) {
  for (const [name, version] of Object.entries(pkg[section] ?? {})) {
    if (!allowed.includes(name)) issues.push(`Unapproved ${section}: ${name}`);
    if (lock.packages?.[""]?.[section]?.[name] !== version) issues.push(`Lock root differs for ${name}`);
  }
}
for (const name of [...policy.introducedRuntime, ...policy.introducedDevelopment]) {
  const version = pkg.dependencies?.[name] ?? pkg.devDependencies?.[name];
  if (!/^\d+\.\d+\.\d+$/.test(version ?? "")) issues.push(`New dependency must be exact and installed: ${name}`);
}
const imports = new Set();
async function scan(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) { await scan(path); continue; }
    if (!/\.tsx?$/.test(entry.name) || /\.test\./.test(entry.name)) continue;
    const source = ts.createSourceFile(path, await readFile(path, "utf8"), ts.ScriptTarget.Latest, true);
    function visit(node) {
      let specifier;
      if ((ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) && node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) specifier = node.moduleSpecifier.text;
      if (ts.isCallExpression(node) && (node.expression.kind === ts.SyntaxKind.ImportKeyword || (ts.isIdentifier(node.expression) && node.expression.text === "require")) && node.arguments[0] && ts.isStringLiteral(node.arguments[0])) specifier = node.arguments[0].text;
      if (specifier && !specifier.startsWith(".") && !specifier.startsWith("@/")) {
        const parts = specifier.split("/");
        imports.add(specifier.startsWith("@") ? parts.slice(0, 2).join("/") : parts[0]);
        const file = relative(root, path).replaceAll("\\", "/");
        if (specifier.startsWith("@base-ui/react") && !file.startsWith("src/components/ui/")) issues.push(`Base UI must use local ui wrappers: ${file}`);
        if (/^(framer-motion|clsx|tailwind-merge|redux|react-redux|zustand\/traditional|react-icons|radix-ui|@radix-ui\/|@mui\/|@headlessui\/|@tabler\/)/.test(specifier) || specifier === "motion" || specifier.startsWith("lucide-react/dynamic")) issues.push(`Duplicate or forbidden library entry ${specifier}: ${file}`);
        if (specifier === "lucide-react" && ts.isImportDeclaration(node) && node.importClause?.namedBindings && ts.isNamespaceImport(node.importClause.namedBindings)) issues.push(`Import only named Lucide icons: ${file}`);
      }
      ts.forEachChild(node, visit);
    }
    visit(source);
  }
}
await scan(resolve(root, "src"));
for (const name of policy.introducedRuntime) if (!imports.has(name)) issues.push(`Unused new runtime dependency: ${name}`);
const versions = {};
for (const name of ["react", "react-dom", "@base-ui/react", "lucide-react", "motion", "framer-motion", "zustand", "react-markdown", "remark-gfm", "unified", "remark-parse", "@types/mdast"]) {
  versions[name] = [...new Set(Object.entries(lock.packages ?? {}).filter(([path]) => path === `node_modules/${name}` || path.endsWith(`/node_modules/${name}`)).map(([, value]) => value.version))];
  if (versions[name].length > 1) issues.push(`Multiple installed versions: ${name} ${versions[name].join(", ")}`);
}
console.log(JSON.stringify({ stage: policy.stage, directRuntime: Object.keys(pkg.dependencies ?? {}).length, versions, issues }, null, 2));
if (issues.length) process.exitCode = 1;

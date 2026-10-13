import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const remixRoot = path.resolve(scriptDir, "..");
const depsRoot = process.env.REMIX_VERIFY_DEPS
  ? path.resolve(process.env.REMIX_VERIFY_DEPS)
  : path.join(remixRoot, ".deps");
const requireFromDeps = createRequire(path.join(depsRoot, "package.json"));
const solc = requireFromDeps("solc");

const sourceFiles = [
  "contracts/UniCredentialSBT.sol",
  "contracts/DisclosureRegistry.sol",
  "contracts/interfaces/IUniCredentialSBT.sol",
  "tests/UniCredentialSBT_test.sol",
  "tests/DisclosureRegistry_test.sol",
];
const sources = Object.fromEntries(
  sourceFiles.map((name) => [
    name,
    { content: fs.readFileSync(path.join(remixRoot, name), "utf8") },
  ]),
);
// The real library is injected by Remix. This minimal compile-time stub lets
// the local verifier validate test syntax without replacing Remix testing.
sources["remix_tests.sol"] = {
  content: `
    pragma solidity >=0.4.22 <0.9.0;
    library Assert {
      function ok(bool, string memory) internal pure {}
      function equal(uint256, uint256, string memory) internal pure {}
      function equal(address, address, string memory) internal pure {}
    }
  `,
};

function resolveImport(importPath) {
  const localImportPath = importPath.replace(
    /^@openzeppelin\/contracts@5\.0\.2\//,
    "@openzeppelin/contracts/",
  );
  const candidates = [
    path.join(remixRoot, importPath),
    path.join(remixRoot, "contracts", importPath),
    path.join(depsRoot, "node_modules", localImportPath),
  ];
  const found = candidates.find((candidate) => fs.existsSync(candidate));
  return found
    ? { contents: fs.readFileSync(found, "utf8") }
    : { error: `Import not found: ${importPath}` };
}

function compile(optimizerEnabled) {
  const input = {
    language: "Solidity",
    sources,
    settings: {
      optimizer: { enabled: optimizerEnabled, runs: 200 },
      outputSelection: {
        "*": { "*": ["evm.deployedBytecode.object"] },
      },
    },
  };
  const output = JSON.parse(solc.compile(JSON.stringify(input), { import: resolveImport }));
  const errors = (output.errors ?? []).filter((entry) => entry.severity === "error");
  if (errors.length) {
    errors.forEach((entry) => console.error(entry.formattedMessage));
    process.exit(1);
  }
  return output.contracts;
}

const limit = 24_576;
let failed = false;
for (const optimizerEnabled of [false, true]) {
  const contracts = compile(optimizerEnabled);
  console.log(`\nOptimizer ${optimizerEnabled ? "ON (runs=200)" : "OFF"}`);
  for (const [sourceName, sourceContracts] of Object.entries(contracts)) {
    if (!sourceName.startsWith("contracts/")) continue;
    for (const [contractName, artifact] of Object.entries(sourceContracts)) {
      const bytecode = artifact.evm.deployedBytecode.object;
      if (!bytecode) continue;
      const size = bytecode.length / 2;
      const status = size <= limit ? "PASS" : "FAIL";
      console.log(`${status.padEnd(4)} ${contractName.padEnd(24)} ${String(size).padStart(6)} bytes`);
      if (size > limit) failed = true;
    }
  }
}

if (failed) {
  console.error(`\nAt least one contract exceeds the EIP-170 ${limit}-byte limit.`);
  process.exit(1);
}
console.log(`\nAll deployable contracts are below the EIP-170 ${limit}-byte limit.`);

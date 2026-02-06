import path from "node:path";

import IdeContextPlugin from "./ide-context-plugin.mjs";

async function main() {
  const workspace = path.resolve(process.argv[2] || process.cwd());
  const prompt = process.argv.slice(3).join(" ") || "Refactor this function";

  const plugin = await IdeContextPlugin({
    directory: workspace,
    worktree: workspace,
  });

  const output = {
    message: {},
    parts: [
      {
        type: "text",
        text: prompt,
      },
    ],
  };

  await plugin["chat.message"](
    {
      sessionID: "smoke",
    },
    output,
  );

  console.log(output.parts[0].text);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

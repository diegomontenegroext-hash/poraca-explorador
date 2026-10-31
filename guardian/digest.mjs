import {readFile,writeFile} from "node:fs/promises";
import {buildDigest} from "./digest-core.mjs";
const folder=new URL("./out/",import.meta.url);
const report=JSON.parse(await readFile(new URL("report.json",folder),"utf8"));
const content=buildDigest(report,{runId:process.env.GITHUB_RUN_ID||report.runId||"",eventName:process.env.GITHUB_EVENT_NAME||""});
await writeFile(new URL("digest.md",folder),content);
console.log("GUARDIAN_DIGEST_CREATED "+report.verdict);

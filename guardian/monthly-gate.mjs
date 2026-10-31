import {appendFile} from "node:fs/promises";
import {shouldRunMonthly} from "./monthly.mjs";
const event=process.env.GITHUB_EVENT_NAME||"manual",month=new Date().toISOString().slice(0,7);
let run=true;
if(event==="schedule"){
 const token=process.env.GH_TOKEN,repo=process.env.GITHUB_REPOSITORY;
 if(!token||!repo)throw Error("Token/repo missing for monthly dedup");
 const endpoint="https://api.github.com/repos/"+repo+"/issues/4/comments?per_page=100&sort=created&direction=desc";
 const r=await fetch(endpoint,{headers:{Authorization:"Bearer "+token,Accept:"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}});
 if(!r.ok)throw Error("Monthly history unavailable HTTP "+r.status);
 run=shouldRunMonthly({event,month,comments:await r.json()});
}
if(process.env.GITHUB_OUTPUT)await appendFile(process.env.GITHUB_OUTPUT,"audit="+(run?"true":"false")+"\n");
console.log(run?"GUARDIAN_MONTHLY_GO "+month:"GUARDIAN_ALREADY_REPORTED "+month);

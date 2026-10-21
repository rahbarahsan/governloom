import {readFile,writeFile} from "node:fs/promises";
import {execFileSync} from "node:child_process";
import {dirname,resolve} from "node:path";
import {chromium,expect} from "@playwright/test";

const config=JSON.parse(await readFile(process.env.CAPTURE_CONFIG,"utf8"));
const directory=dirname(process.env.CAPTURE_CONFIG);
const browser=await chromium.launch(); const scenes=[]; const errors=[];
try {
  const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:"reduce",timezoneId:"UTC"});
  page.on("pageerror",error=>errors.push(error.message));
  async function capture(caption,anchor,duration=4000) {
    await anchor.evaluate(element=>window.scrollTo(0,Math.max(0,element.getBoundingClientRect().top+window.scrollY-40)));
    await page.evaluate(()=>document.fonts.ready);
    const file=`scene-${String(scenes.length+1).padStart(2,"0")}.png`;
    await page.screenshot({path:resolve(directory,file),animations:"disabled"});
    scenes.push({file,caption,duration_ms:duration}); console.log(`Captured ${scenes.length}: ${caption}`);
  }
  await page.goto(config.collector);
  await page.getByLabel("Username",{exact:true}).fill("demo-operator");
  await page.getByLabel("Password",{exact:true}).fill(process.env.CAPTURE_PASSWORD);
  await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await page.getByLabel("Active application").selectOption(config.application_id);
  const panel=page.locator(".discovery-panel");
  await panel.getByText("Import application evidence",{exact:true}).click();
  await panel.getByLabel("Import discovery bundle",{exact:true}).setInputFiles(config.evidence);
  await expect(panel).toContainText("Inferred application:");
  await panel.getByText("Import application evidence",{exact:true}).click();
  await capture("Explore selected source and traces; review the frozen model-assisted application draft",panel);
  const hypotheses=panel.locator(".discovery-summary details");
  await hypotheses.nth(1).locator("summary").click();
  await capture("Inspect an exact source quote supporting an observed boundary and an explicit hypothesis",hypotheses.nth(1));
  await hypotheses.nth(1).locator("summary").click();
  await panel.getByLabel("The actuals/reference labels represent observed outcomes; I reviewed their meaning.",{exact:true}).check();
  await capture("The owner confirms the prefilled understanding and the meaning of actual outcomes",panel.locator("form"));
  await panel.getByRole("button",{name:"Confirm application understanding",exact:true}).click();
  await expect(panel).toContainText("Application understanding confirmed");
  await panel.getByRole("button",{name:"Evaluate monitoring proposal",exact:true}).click();
  await expect(panel).toContainText("24 calibration · 48 held-out");
  const proposal=panel.locator(".discovery-plan");
  await proposal.getByText(/Forecast outcome error · available/).click();
  await capture("Prepare a frozen evaluation set and quantify forecast errors using calibration-only thresholds",proposal);
  await proposal.getByText(/Forecast outcome error · available/).click();
  await proposal.getByLabel("I reviewed the measurements and limitations; activate flags only.",{exact:true}).check();
  await capture("Held-out alert-budget warnings remain visible before observation activation",proposal);
  await proposal.getByRole("button",{name:"Activate observation policy",exact:true}).click();
  await expect(panel).toContainText("Observation policy activated");
  const token=(await(await page.request.post(config.collector+"/api/auth/login",{data:{username:"demo-operator",password:process.env.CAPTURE_PASSWORD}})).json()).token;
  async function api(path,body) {
    const response=await fetch(config.collector+"/api"+path,{redirect:"error",headers:{Authorization:"Bearer "+token,...(body ? {"Content-Type":"application/json"}:{})},...(body ? {method:"POST",body:JSON.stringify(body)}:{})});
    if(!response.ok) throw new Error(`Capture API rejected ${path}: ${response.status}`); return response.json();
  }
  const plans=await api(`/applications/${config.application_id}/discovery-plans`);
  const plan=await api(`/applications/${config.application_id}/discovery-plans/${plans[0].id}`);
  const key=await api(`/applications/${config.application_id}/ingest-keys`,{name:"actual-forecast-capture",actor:"demo-operator"});
  const result=JSON.parse(execFileSync(process.env.CAPTURE_PYTHON,["-m","scripts.capture_discovery","--emit"],{
    input:JSON.stringify({endpoint:config.collector,key:key.key,plan,snapshot:config.snapshot}),encoding:"utf8",windowsHide:true,timeout:30000}));
  const incident=page.locator(".runtime-incident").first();
  await expect(incident).toContainText("Forecast error above historical baseline");
  await capture("An actual NOAA forecast and observed actual produce a flag and open incident through the prepared mapping",incident);
  if(errors.length) throw new Error(errors.join("\n"));
  await writeFile(resolve(directory,"manifest.json"),JSON.stringify({schema_version:1,source:"Actual Chromium discovery/confirmation/calibration and public-mapper forecast incident",
    demo:"Scripted named operator; replayed real model analysis; actual NOAA model inference; no independent owner study",
    provenance:{...config.provenance,dataset_sha256:plan.dataset.sha256,actual_forecast:result},scenes},null,2));
} finally {await browser.close();}

import {expect,test} from "@playwright/test";

test("late initial application response preserves the owner's selection",async({page,request})=>{
  const apps=[];
  for(const name of ["Initial application", "Owner selected application"]) {
    const response=await request.post("http://127.0.0.1:8000/api/applications",{data:{name,purpose:"Selection race regression",owner:"Owner",expected_behavior:"Preserve explicit selection"}});
    apps.push(await response.json());
  }
  let release!:()=>void; let delivered!:()=>void; let arrivals=0;
  const gate=new Promise<void>(resolve=>{release=resolve;});
  const staleDelivered=new Promise<void>(resolve=>{delivered=resolve;});
  await page.route("**/api/applications",async route=>{
    if(route.request().method()!=="GET") return route.continue();
    const number=++arrivals;
    if(number===2) await gate;
    await route.fulfill({json:apps});
    if(number===2) delivered();
  });
  await page.goto("/");
  await expect.poll(()=>arrivals).toBeGreaterThanOrEqual(2);
  await page.getByLabel("Active application").selectOption(apps[1].id);
  await expect(page.locator(".topbar")).toContainText("Owner selected application");
  release(); await staleDelivered;
  // Let the delivered JSON continuation and its React render finish.
  await page.evaluate(()=>new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve()))));
  await expect(page.getByLabel("Active application")).toHaveValue(apps[1].id);
  await page.getByRole("button",{name:"Refresh",exact:true}).click();
  await expect(page.locator(".topbar")).toContainText("Owner selected application");
});

test("compose tool and citation policies, confirm permissions and retain a deferral",async({page,request})=>{
  const traces=Array.from({length:8},(_,index)=>({tool_name:index%2 ? "search":"delete",citations:["doc"],source_ids:["doc"],latency_ms:index+10,
    group_id:`g-${index}`,split:index<4 ? "calibration":"held_out",model_version:"tools-model",application_version:"tools-service"}));
  await page.goto("/");
  await page.getByRole("button",{name:/01.*applications/i}).click();
  await page.locator(".discovery-start").getByLabel("Application name",{exact:true}).fill("Policy composition browser fixture");
  await page.getByLabel("Application evidence bundle",{exact:true}).setInputFiles({name:"tools.json",mimeType:"application/json",buffer:Buffer.from(JSON.stringify({actor:"fixture",traces}))});
  await page.getByRole("button",{name:"Explore application evidence",exact:true}).click();
  const panel=page.locator(".discovery-panel");
  await page.getByLabel("Monitoring operator",{exact:true}).fill("Browser owner");
  await panel.getByRole("button",{name:"Confirm application understanding",exact:true}).click();
  await expect(panel).toContainText("Application understanding confirmed");
  await panel.getByRole("button",{name:"Evaluate monitoring proposal",exact:true}).click();
  await expect(panel.locator('[data-control="tools.permissions"]')).toContainText("needs evidence");
  await panel.getByLabel("Permitted tools (comma separated)").fill("search");
  await expect(panel.getByRole("button",{name:"Activate observation policy",exact:true})).toBeDisabled();
  await panel.getByRole("button",{name:"Confirm application understanding",exact:true}).click();
  await panel.getByRole("button",{name:"Evaluate monitoring proposal",exact:true}).click();
  await expect(panel.locator('[data-control="tools.permissions"]')).toContainText("ready");
  const citations=panel.locator('[data-control="rag.citations"]');
  await citations.getByText("Record why this recommendation is deferred",{exact:true}).click();
  await citations.getByLabel("Defer Flag missing or unknown citations",{exact:true}).check();
  await expect(panel.getByRole("button",{name:"Save policy selection and reevaluate",exact:true})).toBeDisabled();
  await citations.getByLabel("Reason for deferring Flag missing or unknown citations",{exact:true}).fill("Owned test focuses on tool permissions; citation monitoring deferred for review");
  await panel.getByRole("button",{name:"Save policy selection and reevaluate",exact:true}).click();
  await expect(panel).toContainText("Policy selection recorded");
  await panel.getByLabel("I reviewed the measurements and limitations; activate flags only.",{exact:true}).check();
  await panel.getByRole("button",{name:"Activate observation policy",exact:true}).click();
  await expect(panel).toContainText("Observation policy activated");
  const apps=await(await request.get("http://127.0.0.1:8000/api/applications")).json();
  const app=apps.find((item:{name:string})=>item.name==="Policy composition browser fixture");
  const prefix=`http://127.0.0.1:8000/api/applications/${app.id}`;
  const plans=await(await request.get(prefix+"/discovery-plans")).json();
  const plan=plans.find((item:{control_decisions:{dismissed:Record<string,string>}})=>item.control_decisions.dismissed["rag.citations"]);
  expect(plan.control_decisions.selected).toEqual(["tools.permissions"]);
  const policy=await(await request.get(prefix+"/monitor-policy")).json();
  expect(policy.rules).toHaveLength(1);
  expect(policy.rules[0].allowed).toEqual(["search"]);
  const key=await(await request.post(prefix+"/ingest-keys",{data:{name:"browser-tool",actor:"Owner"}})).json();
  const response=await request.post("http://127.0.0.1:8000/api/runtime/events",{headers:{Authorization:`Bearer ${key.key}`},data:{phase:"tool",trace_id:"browser-tool",task_type:"rag",model_version:"tools-model",application_version:"tools-service",tool_name:"delete",client_mode:"observe"}});
  expect((await response.json()).action).toBe("flag");
  await expect(page.locator(".runtime-incident").getByText("Policy reference: tools.permissions",{exact:true})).toBeVisible();
  await page.reload();
  await expect(page.locator(".discovery-panel").getByLabel("Permitted tools (comma separated)")).toHaveValue("search");
});

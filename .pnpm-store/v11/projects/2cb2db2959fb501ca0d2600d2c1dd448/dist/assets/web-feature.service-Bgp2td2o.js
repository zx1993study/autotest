import{c as u}from"./createLucideIcon-DwVWmYwy.js";import{I as a}from"./index-DH8OPOfd.js";/**
 * @license lucide-vue-next v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const $=u("loader-circle",[["path",{d:"M21 12a9 9 0 1 1-6.219-8.56",key:"13zald"}]]),o="/web-testing/features",d=(e,t,s,r)=>a({method:"POST",url:"/web-testing/execution-summaries",data:{project_id:e,scope:t,ids:s},signal:r}),i=e=>a({method:"GET",url:`${o}/${e}`}),m=(e,t,s)=>a({method:s?"PUT":"POST",url:`/web-testing/page-groups/${e}/features${s?`/${s}`:""}`,data:t}),l=e=>a({method:"DELETE",url:`${o}/${e}`}),p=(e,t,s={})=>a({method:"POST",url:`${o}/${e}/${t}`,data:s,...t==="run"?{timeout:6e4}:{}}),b=(e,t,s)=>a({method:s?"PUT":"POST",url:`${o}/${e}/input-cases${s?`/${s}`:""}`,data:t}),T=(e,t)=>a({method:"DELETE",url:`${o}/${e}/input-cases/${t}`}),h=(e,t,s="")=>a({method:"POST",url:`/agent/tasks/${e}/web-control`,data:{action:t,nonce:s}}),g=(e,t)=>a({method:"GET",url:`${o}/${e}/script`,params:{version_id:t}});export{$ as L,T as a,m as b,d as c,l as d,g as e,p as f,i as g,b as s,h as w};

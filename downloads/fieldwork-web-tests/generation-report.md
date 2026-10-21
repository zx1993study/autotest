# 管理端 Web 脚本生成报告

源码版本：`250b6bc4d4e56f1e5136f701e1344590fd24e849`

已有用例保留，不新建重复用例。source_ready 仅表示源码已生成，不表示页面回放或业务测试通过。

## 已有用例

| 用例 ID | 功能 ID | 名称 | 状态 | 说明 |
|---:|---:|---|---|---|
| 33 | 11880 | [正常流程] 活动模板新增 | blocked | Recorded steps require business/input/assertion review before conversion |
| 32 | 11515 | [正常流程] 删除仓库 | blocked | Legacy delete has no owned record ID/row scope; historical records must not be selected |
| 31 | 11512 | [正常流程] 仓库查询 | source_ready | Source toolbar replaces hidden legacy form; original input values retained |
| 28 | 11513 | [正常流程] 新增仓库 | blocked | Recorded steps require business/input/assertion review before conversion |
| 27 | 10013 | [必填为空] 登录页 - Web 必填为空模板 | blocked | Legacy login has no reliable expected outcome; requires per-case credentials/captcha and assertion review |
| 26 | 10013 | [必填为空] 登录页 - Web 必填为空模板 | blocked | Legacy login has no reliable expected outcome; requires per-case credentials/captcha and assertion review |
| 25 | 10013 | [必填为空] 登录页 - Web 必填为空模板 | blocked | Legacy login has no reliable expected outcome; requires per-case credentials/captcha and assertion review |
| 21 | 11513 | [正常流程] 新增仓库 | blocked | Recorded steps require business/input/assertion review before conversion |
| 9 | 10013 | [正常流程] 登录页 | blocked | Legacy login has no reliable expected outcome; requires per-case credentials/captcha and assertion review |
| 5 | 10013 | 账号为空 | blocked | Legacy login has no reliable expected outcome; requires per-case credentials/captcha and assertion review |
| 2 | 10013 | [正常流程] 登录页 | blocked | Legacy login has no reliable expected outcome; requires per-case credentials/captcha and assertion review |

## 页面功能脚本

| 功能 ID | 路由 | 类型 | 状态 | 说明 |
|---:|---|---|---|---|
| 11880 | /system/activity-template-config | page | blocked | Feature name describes a business action but stored type is page; review classification first |
| 11531 | /warehouse/purchase-in-order | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11530 | /visitPlan/visitPlan/list | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11529 | /visitPlan/terminalInventory | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11528 | /system/mcp | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11527 | /order/sales-order | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11526 | /order/productTransaction | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11525 | /order/outboundOrder | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11524 | /approval/myApprove | edit | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11523 | /approval/myApply | edit | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11522 | /activity/apply | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11521 | /index | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11517 | /warehouse/warehouse | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11516 | /warehouse/warehouse | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11515 | /warehouse/warehouse | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11514 | /warehouse/warehouse | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11513 | /warehouse/warehouse | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11512 | /warehouse/warehouse | query | source_ready | Generated from source; real DOM replay still required |
| 11511 | /warehouse/warehouse | page | source_ready | Generated from source; real DOM replay still required |
| 11510 | /warehouse/purchase-in-order | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11509 | /warehouse/purchase-in-order | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11508 | /warehouse/purchase-in-order | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11507 | /warehouse/purchase-in-order | query | source_ready | Generated from source; real DOM replay still required |
| 11506 | /warehouse/purchase-in-order | page | source_ready | Generated from source; real DOM replay still required |
| 11505 | /warehouse | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11504 | /visitPlan/visitReport/list | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11503 | /visitPlan/visitReport/list | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11502 | /visitPlan/visitReport/list | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11501 | /visitPlan/visitReport/list | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11500 | /visitPlan/visitReport/list | query | blocked | No stable unconditional table header; visibility alone is not a business assertion |
| 11499 | /visitPlan/visitReport/list | page | blocked | No stable unconditional table header; visibility alone is not a business assertion |
| 11498 | /visitPlan/visitPlan/list | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11497 | /visitPlan/visitPlan/list | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11496 | /visitPlan/visitPlan/list | query | blocked | List request cannot be uniquely linked to getList; no guessed endpoint is used |
| 11495 | /visitPlan/visitPlan/list | page | source_ready | Generated from source; real DOM replay still required |
| 11494 | /visitPlan/visit-template | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11493 | /visitPlan/visit-template | import | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11492 | /visitPlan/visit-template | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11491 | /visitPlan/visit-template | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11490 | /visitPlan/visit-template | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11489 | /visitPlan/visit-template | query | source_ready | Generated from source; real DOM replay still required |
| 11488 | /visitPlan/visit-template | page | source_ready | Generated from source; real DOM replay still required |
| 11487 | /visitPlan/terminalInventory | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11486 | /visitPlan/terminalInventory | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11485 | /visitPlan/terminalInventory | query | blocked | List request cannot be uniquely linked to getList; no guessed endpoint is used |
| 11484 | /visitPlan/terminalInventory | page | source_ready | Generated from source; real DOM replay still required |
| 11483 | /tool/swagger | page | blocked | A unique top-level list table cannot be proven from source |
| 11482 | /tool/build | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11481 | /tool/build | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11480 | /tool/build | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11479 | /tool/build | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11478 | /tool/build | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11477 | /tool/build | page | blocked | A unique top-level list table cannot be proven from source |
| 11476 | /system/workflow | delete | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11475 | /system/workflow | edit | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11474 | /system/workflow | query | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11473 | /system/workflow | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11472 | /system/role | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11471 | /system/role | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11470 | /system/role | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11469 | /system/role | query | blocked | Query uses a custom/dynamic toolbar; needs a page-specific adapter |
| 11468 | /system/role | page | source_ready | Generated from source; real DOM replay still required |
| 11467 | /system/post | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11466 | /system/post | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11465 | /system/post | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11464 | /system/post | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11463 | /system/post | query | blocked | Query uses a custom/dynamic toolbar; needs a page-specific adapter |
| 11462 | /system/post | page | source_ready | Generated from source; real DOM replay still required |
| 11461 | /system/menu | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11460 | /system/menu | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11459 | /system/menu | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11458 | /system/menu | query | blocked | Query uses a custom/dynamic toolbar; needs a page-specific adapter |
| 11457 | /system/menu | page | source_ready | Generated from source; real DOM replay still required |
| 11456 | /system/mcp | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11455 | /system/mcp | query | blocked | A unique top-level list table cannot be proven from source |
| 11454 | /system/mcp | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11453 | /system/mcp | page | blocked | A unique top-level list table cannot be proven from source |
| 11452 | /system/log/operlog | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11451 | /system/log/operlog | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11450 | /system/log/operlog | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11449 | /system/log/operlog | query | blocked | Query uses a custom/dynamic toolbar; needs a page-specific adapter |
| 11448 | /system/log/operlog | page | source_ready | Generated from source; real DOM replay still required |
| 11447 | /system/dept | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11446 | /system/dept | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11445 | /system/dept | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11444 | /system/dept | query | blocked | Query uses a custom/dynamic toolbar; needs a page-specific adapter |
| 11443 | /system/dept | page | source_ready | Generated from source; real DOM replay still required |
| 11442 | /system/config | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11441 | /supervision/task | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11440 | /supervision/task | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11439 | /supervision/task | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11438 | /supervision/task | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11437 | /supervision/task | query | source_ready | Generated from source; real DOM replay still required |
| 11436 | /supervision/task | page | source_ready | Generated from source; real DOM replay still required |
| 11435 | /product/list | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11434 | /product/list | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11433 | /product/list | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11432 | /product/list | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11431 | /product/list | query | blocked | List request cannot be uniquely linked to getList; no guessed endpoint is used |
| 11430 | /product/list | page | source_ready | Generated from source; real DOM replay still required |
| 11429 | /order/stockInOrder | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11428 | /order/stockInOrder | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11427 | /order/stockInOrder | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11426 | /order/stockInOrder | query | source_ready | Generated from source; real DOM replay still required |
| 11425 | /order/stockInOrder | page | source_ready | Generated from source; real DOM replay still required |
| 11424 | /order/sales-order | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11423 | /order/sales-order | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11422 | /order/sales-order | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11421 | /order/sales-order | query | source_ready | Generated from source; real DOM replay still required |
| 11420 | /order/sales-order | page | source_ready | Generated from source; real DOM replay still required |
| 11419 | /order/return | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11418 | /order/return | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11417 | /order/return | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11416 | /order/return | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11415 | /order/return | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11414 | /order/return | query | source_ready | Generated from source; real DOM replay still required |
| 11413 | /order/return | page | source_ready | Generated from source; real DOM replay still required |
| 11412 | /order/productTransaction | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11411 | /order/productTransaction | query | blocked | No stable unconditional table header; visibility alone is not a business assertion |
| 11410 | /order/productTransaction | page | blocked | No stable unconditional table header; visibility alone is not a business assertion |
| 11409 | /order/outboundOrder | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11408 | /order/outboundOrder | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11407 | /order/outboundOrder | query | source_ready | Generated from source; real DOM replay still required |
| 11406 | /order/outboundOrder | page | source_ready | Generated from source; real DOM replay still required |
| 11405 | /monitor/online | page | source_ready | Generated from source; real DOM replay still required |
| 11404 | /monitor/job | page | source_ready | Generated from source; real DOM replay still required |
| 11403 | /monitor/cacheList | page | blocked | A unique top-level list table cannot be proven from source |
| 11402 | /monitor/cache | page | blocked | A unique top-level list table cannot be proven from source |
| 11401 | /monitor | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11400 | /customer/kol | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11399 | /customer/kol | import | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11398 | /customer/kol | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11397 | /customer/kol | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11396 | /customer/kol | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11395 | /customer/kol | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11394 | /customer/kol | query | source_ready | Generated from source; real DOM replay still required |
| 11393 | /customer/kol | page | source_ready | Generated from source; real DOM replay still required |
| 11392 | /customer/kol | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11391 | /customer/kol | import | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11390 | /customer/kol | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11389 | /customer/kol | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11388 | /customer/kol | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11387 | /customer/kol | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11386 | /customer/kol | query | source_ready | Generated from source; real DOM replay still required |
| 11385 | /customer/kol | page | source_ready | Generated from source; real DOM replay still required |
| 11384 | /customer/directly | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11383 | /customer/directly | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11382 | /customer/directly | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11381 | /customer/directly | import | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11380 | /customer/directly | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11379 | /customer/directly | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11378 | /customer/directly | query | source_ready | Generated from source; real DOM replay still required |
| 11377 | /customer/directly | page | source_ready | Generated from source; real DOM replay still required |
| 11376 | /customer/directly | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11375 | /customer/directly | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11374 | /customer/directly | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11373 | /customer/directly | import | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11372 | /customer/directly | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11371 | /customer/directly | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11370 | /customer/directly | query | source_ready | Generated from source; real DOM replay still required |
| 11369 | /customer/directly | page | source_ready | Generated from source; real DOM replay still required |
| 11368 | /customer/business | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11367 | /customer/business | import | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11366 | /customer/business | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11365 | /customer/business | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11364 | /customer/business | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11363 | /customer/business | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11362 | /customer/business | query | source_ready | Generated from source; real DOM replay still required |
| 11361 | /customer/business | page | source_ready | Generated from source; real DOM replay still required |
| 11360 | /customer/business | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11359 | /customer/business | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11358 | /customer/business | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11357 | /customer/business | import | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11356 | /customer/business | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11355 | /customer/business | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11354 | /customer/business | query | source_ready | Generated from source; real DOM replay still required |
| 11353 | /customer/business | page | source_ready | Generated from source; real DOM replay still required |
| 11352 | /customer | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11351 | /approval/todo | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11348 | /user/profile | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11347 | /user/profile | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11346 | /user/profile | page | blocked | A unique top-level list table cannot be proven from source |
| 11345 | /system/user | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11344 | /system/user | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11343 | /system/user | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11342 | /system/user | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11341 | /system/user | query | blocked | Query uses a custom/dynamic toolbar; needs a page-specific adapter |
| 11340 | /system/user | page | source_ready | Generated from source; real DOM replay still required |
| 11339 | /system/dict-data/index/:dictId | export | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11338 | /system/dict-data/index/:dictId | detail | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11337 | /system/dict-data/index/:dictId | delete | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11336 | /system/dict-data/index/:dictId | edit | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11335 | /system/dict-data/index/:dictId | add | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11334 | /system/dict-data/index/:dictId | query | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11333 | /system/dict-data/index/:dictId | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11332 | /system/dict | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11331 | /system/dict | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11330 | /system/dict | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11329 | /system/dict | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11328 | /system/dict | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11327 | /system/dict | query | blocked | Query uses a custom/dynamic toolbar; needs a page-specific adapter |
| 11326 | /system/dict | page | source_ready | Generated from source; real DOM replay still required |
| 11325 | /system/config | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11324 | /system/config | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11323 | /system/config | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 11322 | /system/config | query | blocked | Query uses a custom/dynamic toolbar; needs a page-specific adapter |
| 11321 | /system/config | page | source_ready | Generated from source; real DOM replay still required |
| 11320 | /business/warehouse/inventory | export | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11319 | /business/warehouse/inventory | edit | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11318 | /business/warehouse/inventory | query | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11317 | /business/warehouse/inventory | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11316 | /business/warehouse | export | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11315 | /business/warehouse | delete | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11314 | /business/warehouse | detail | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11313 | /business/warehouse | edit | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11312 | /business/warehouse | add | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11311 | /business/warehouse | query | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11310 | /business/warehouse | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11309 | /business/purchase-in-order | export | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11308 | /business/purchase-in-order | edit | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11307 | /business/purchase-in-order | delete | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11306 | /business/purchase-in-order | detail | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11305 | /business/purchase-in-order | add | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11304 | /business/purchase-in-order | query | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11303 | /business/purchase-in-order | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11302 | /business/return | export | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11301 | /business/return | add | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11300 | /business/return | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11299 | /business/productTransaction | export | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11298 | /business/productTransaction | query | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11297 | /business/productTransaction | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11296 | /business/terminalInventory | export | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11295 | /business/terminalInventory | detail | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11294 | /business/terminalInventory | query | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 11293 | /business/terminalInventory | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 10846 | /approval/todo | query | blocked | A unique top-level list table cannot be proven from source |
| 10845 | /approval/todo | page | blocked | A unique top-level list table cannot be proven from source |
| 10844 | /approval/notice | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10843 | /approval/notice | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10842 | /approval/notice | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10841 | /approval/notice | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10840 | /approval/notice | query | source_ready | Generated from source; real DOM replay still required |
| 10839 | /approval/notice | page | source_ready | Generated from source; real DOM replay still required |
| 10838 | /approval/myApprove | export | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 10837 | /approval/myApprove | detail | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 10836 | /approval/myApprove | query | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 10835 | /approval/myApprove | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 10834 | /approval/myApply | export | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 10833 | /approval/myApply | detail | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 10832 | /approval/myApply | query | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 10831 | /approval/myApply | page | blocked | Route/component is absent or cannot be parsed; no guessed alias is used |
| 10830 | /activity/payment | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10829 | /activity/payment | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10828 | /activity/payment | query | source_ready | Generated from source; real DOM replay still required |
| 10827 | /activity/payment | page | source_ready | Generated from source; real DOM replay still required |
| 10826 | /activity/participant | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10825 | /activity/participant | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10824 | /activity/participant | query | source_ready | Generated from source; real DOM replay still required |
| 10823 | /activity/participant | page | source_ready | Generated from source; real DOM replay still required |
| 10822 | /activity/list | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10821 | /activity/list | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10820 | /activity/list | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10819 | /activity/list | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10818 | /activity/list | query | blocked | List request cannot be uniquely linked to getList; no guessed endpoint is used |
| 10817 | /activity/list | page | source_ready | Generated from source; real DOM replay still required |
| 10816 | /activity/apply | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10815 | /activity/apply | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10814 | /activity/apply | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10813 | /activity/apply | add | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10812 | /activity/apply | query | source_ready | Generated from source; real DOM replay still required |
| 10811 | /activity/apply | page | source_ready | Generated from source; real DOM replay still required |
| 10810 | /index | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10809 | /index | query | blocked | A unique top-level list table cannot be proven from source |
| 10808 | /system/log/logininfor | export | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10807 | /system/log/logininfor | edit | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10806 | /system/log/logininfor | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10805 | /system/log/logininfor | delete | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10804 | /system/log/logininfor | query | blocked | Query uses a custom/dynamic toolbar; needs a page-specific adapter |
| 10803 | /system/log/logininfor | page | source_ready | Generated from source; real DOM replay still required |
| 10802 | /index | page | blocked | A unique top-level list table cannot be proven from source |
| 10801 | /index | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10800 | /index | detail | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |
| 10799 | /index | query | blocked | A unique top-level list table cannot be proven from source |
| 10798 | /index | query | blocked | A unique top-level list table cannot be proven from source |
| 10797 | /index | query | blocked | A unique top-level list table cannot be proven from source |
| 10796 | /index | page | blocked | A unique top-level list table cannot be proven from source |
| 10013 | /login | login | blocked | Requires confirmed business steps, run-owned fixtures and explicit write approval |

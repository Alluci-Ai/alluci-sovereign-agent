# Changelog

## [6.5.0-stable-grounding-dossier](https://github.com/Alluci-Ai/alluci-sovereign-agent/compare/v6.4.1-stable-grounding-dossier...v6.5.0-stable-grounding-dossier) (2026-09-03)


### Features

* **cognitive-engine:** implement 5-tier conversational bandwidth spectrum and 9-genre epistemic ontology ([58ec339](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/58ec3392220e027c634fd3e70c5f07604baa75e2))
* **config:** make loop breaker substantive token counts and repetition thresholds fully dynamic ([edc4e1c](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/edc4e1cbcee8b942960e07f5877572903f2b1e1d))
* **directives:** implement 6 dynamic cognitive modalities and in-stream URL scraping & context binding ([cafcc66](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/cafcc668738eab41d0d0c3127b13130953872345))
* **dreaming:** host timezone scanner, configurable quiet-hours schedule, GPU preemption, and pure academic grounding ([6e8860c](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/6e8860c7b15d2effd17c9941fb107d7fce05c067))
* eliminate document context bleed via attachment priority, single-doc isolation, and closed-world directive quarantine ([167c0d0](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/167c0d02594f413715ea283d8f53c436ff5943f2))
* enhance visual figure rendering, lightbox pan-zoom, dual links, triad bundling, and PCL schema ([cbe143e](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/cbe143ef49d8c21a8ccfb5ce04adb752416c9755))
* **grounding:** implement dynamic intent-driven directives and cryptographic SHA-256 memory scoping ([dd7b46e](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/dd7b46e8919ffd1576bd3fa038936a18078960dc))
* **inference:** implement 3-layer anti-degeneration architecture, nucleus sampling, repetition penalties, and real-time loop circuit breaker ([2439e0e](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/2439e0eeddb44a0bcc00f77c2f824fefea1dcb6d))
* **memory:** add dedicated purge_l3 endpoint and protect chat history from memory reset ([587d9ad](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/587d9ad833bfc3fea46a106ff530ca8bf7a60659))
* **memory:** restore classic H-LSM layout, add purge_all endpoint, and harden grounding isolation ([aa0a362](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/aa0a36244d618808b15abda2676a1f6a8f6608d9))
* **monograph:** enforce unescaped figure embeds, clickable links, strict KaTeX continuity, and chapter narrative depth ([b6eccdc](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/b6eccdcfbdef5653c22715e4f94513edf41da64d))
* **monograph:** implement 10-layer monograph engine, dynamic math harvester, and KaTeX rendering ([d9a857f](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/d9a857f6fac51215994b101d6bc3712ccdcd69a0))
* **monograph:** unify intent decomposition priority, multimodal figure embedding directives, and chat file grounding ([31f2a22](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/31f2a229080fe07787dd7bff28cc9fd62e548090))
* **multimodal:** add dynamic technical figure extraction, VPI dual-pass filtering, 4-tier H-LSM graph indexing, and artifact triad bundling ([3dd5e4d](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/3dd5e4d22960a8cc39cf517f13add3fd17efdd14))
* **multimodal:** unify chat file upload ingestion with VPI figure extraction and H-LSM wiring ([1840df8](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/1840df8eb1da348243b43a4fc26f0f96b2cc0e83))


### Bug Fixes

* **gemini,pcl:** use walrus operator for regex match narrowing and simplify opp_id ([e2d7f0b](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/e2d7f0b81fb1123184427aecd56bc18c96db1851))
* **hlsm:** convert betti_signature to string in L2 insert and harden page text validation ([8c063ca](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/8c063cad85a46a8400fa543b0b90636aa5525021))
* **hlsm:** use _extract_kuzu_rows in purge_l3 to handle list and iterable query results safely ([ff29cc8](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/ff29cc8e78855e48e6bf06a2d40c86d4826ceb71))
* **inference:** add syntax delimiter immunity to MLX loop breaker to prevent premature markdown truncation ([24da45b](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/24da45b22ba0da43e49a4d7d6e14e7b7a755572e))
* **inference:** eliminate 1-gram false aborts and add LaTeX formatting immunity to MLX streaming loop breaker ([56dfcda](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/56dfcdacaa73ee21ed39aef7f240c04ecf079a00))
* **memory:** clean L1 text storage, eliminate page delimiter title pollution, and sandbox test artifacts ([22637a4](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/22637a4f82be5d9471084f1cc507828faf33373d))
* **pcl:** make CodeHealthDetector inherit from BaseDetector, fix session mock, and resolve type annotations ([80a3ef5](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/80a3ef52ca97c62ca80ab31c2f5579da9406eb35))
* **types:** resolve static typing and nullability checks in vpi.py ([4fe6447](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/4fe644761a4a85ff9e9a9abce11eef4384eeda15))
* **types:** type annotate document grounding iterables and resolve CronRun / SQLModel typing ([16f6f07](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/16f6f075893361c596ff4a3006db44026198c088))
* **vpi:** refine processor type annotations and null safety checks ([2a0ee82](https://github.com/Alluci-Ai/alluci-sovereign-agent/commit/2a0ee82ac0cb050de3b5af59109c0f44f5a9a19a))

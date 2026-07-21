# Fresh browser proof — `/content-workflow`

This proof was generated from the running dashboard after a managed stack
restart on 2026-07-21. It is the current route state, not a copied baseline.

```text
HEAD: 02f05d88699f854452f5da543359e5e8b54d4c2a
URL: http://127.0.0.1:5173/content-workflow?work_item_id=content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca
desktop: 1440x900, scrollY=0, scrollWidth=1440
mobile: 390x844, scrollY=0, scrollWidth=390
snapshot: HTTP 200
```

The worktree had unrelated pre-existing review-packet cleanup changes; no
product source was modified after this HEAD. The five image hashes are:

```text
desktop-1440x900.png  62913aa7a5d7aba9d564125491393f94c1c6a1902cba5bde80ad86a230208fdb
mobile-390x844.png    247c0a86c031b761e944fee57d39320a34b1a0eb34d9c050e6b55dc69a02b676
sources-open.png      679059b7551a9947d40c3b19ba5dc8b6ebff462665f34bcccdbdbf4e041f660d
desktop-full.png      7fbd22934efa2989cdf72c82839734eef83f52a2269d9842e3380b77c7c29730
mobile-full.png       53ebf034490f91350c064dd29778eea378234297bb8a197f18729eb07c7f2dfa
```

`network.log` contains the deduplicated API request log from load through the
source-details interaction. Every listed request is `GET` and returned `200`;
there is no workflow mutation, revision creation, generation, review,
handoff, or WordPress write.

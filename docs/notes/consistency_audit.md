# Consistency audit — docs, checks and tests against the netlist

Date: 2026-09-17. Branch `ring-coarse-tune`.
Reference for "the design": `sim/netlists/blocks.inc` (mtime 2026-09-16 23:50:28,
newer than every `xschem/*.sch`) and the logs in `sim/results/`.
No simulation was run for this audit; nothing outside `docs/notes/` was modified.

Ordered by how much a reader would be misled.

---

## 1. Stale or unsupported numbers

**25 distinct claims**, across `README.md`, `CLAUDE.md` and six documents.
The three that matter most are 1.1, 1.3 and 1.6.

### 1.1 The 11 kΩ ring load was never applied to the design

`docs/EXPERIMENTS.md:377` — "with the load resistors at **11 kohm** (trim width
unchanged at 4 um)" — and everything derived from it in §2.15 (`:381`, `:385`,
`:386`).

The design is still at **10 000 Ω**:

- `sim/netlists/blocks.inc:450-451`
  `XR1 VDD vo+ sub! rhigh w=1.000000e-06 l=6.945882e-06 ...`
  Solving the PDK expression the decks use,
  `Lload = (R − 1.6e-4/W)·(W − 0.04u)/1360` (`sim/decks/ring_ct.inc:108`),
  `l = 6.945882e-06` ⇒ **R = 10 000 Ω**. 11 000 Ω would be `l = 7.651765e-06`.
- `tools/port_from_sky130.py:236-237`
  `("ring_inverter", "R1"): {"R": 10000},` / `("ring_inverter", "R2"): {"R": 10000},`
- `sim/decks/ring_ct.inc:105` `.param Rload=10000`

11 000 Ω exists only as a sweep override in the untracked deck
`sim/decks/ring_bracket.spice:49` `alterparam Rload = 11000`, and
`sim/results/apply_verify.out` contains one line — `[04:43] waiting for the
simulator` — so `tools/apply_ring_sizing.py` never completed. Everything §2.15
claims therefore describes a circuit that is not in `blocks.inc`.

### 1.2 "24 of 27 corners bracketed" is 21 of 27 in its own log

`docs/EXPERIMENTS.md:381-382` — "bracketed at **24 of 27** corners outright. The
three ss rows flagged otherwise (ss/-40 C/1.08 V, ss/-40 C/1.32 V, ss/27 C/1.08 V)
have zero swing at the slow test point".

`sim/results/ring_bracket.out` has **six** ss corners with no usable slow-end
point: the three named ones are absent from the log entirely (only the `p_pt 2`
row was printed), and three more were printed with no swing —

    ss -40 C 1.20 V  p_pt 1  fosc 2.490837e+08  swing 0.000000e+00
    ss  27 C 1.20 V  p_pt 1  fosc 3.530615e+08  swing 0.000000e+00
    ss  27 C 1.32 V  p_pt 1  fosc 3.690668e+08  swing 4.000000e-05

The fast-end figures in the same entry do check out: min `6.181017e+08` at
ss/125 C/1.08 V (= 618.1 MHz, `:386`) and max `1.064462e+09` (= "618-1064 MHz",
`:385`).

### 1.3 The pump bias cell's size, and its currents

| claim | file:line | actual | evidence |
|---|---|---|---|
| `XMN1  nMOS W 0.5 / L 8 µm` | `docs/HANDBOOK.md:737` | W **0.25 µm** | `blocks.inc:325` `XMN1 bias_p vbias VSS VSS sg13_lv_nmos w=2.500000e-07 l=8.000000e-06` |
| nominal up/down **790 / 806 nA** | `docs/HANDBOOK.md:743` | **416 / 450 nA** | `sim/results/cp_ibias_check.log`, T 27 / VDD 1.2 / vout 0.6: `i_up_na = 4.163051e+02`, `i_dn_na = 4.501831e+02` |
| up **715-894 nA** across corners | `docs/HANDBOOK.md:743`, `docs/EXPERIMENTS.md:150` | up **392.7-437.9 nA** | same log, 27 rows |
| **±0.90 µA** / "0.90 µA per phase" | `docs/HANDBOOK.md:167`, `:181`, `README.md:88` | 0.42 / 0.45 µA | same log |
| mismatch **11.0 %** | `docs/HANDBOOK.md:184`, `:382`, `:496`, `docs/RING_DUAL_LOOP.md:72`, `tools/run_checks.py:155` | **−7.8 %** at the lock point (−4.8 … −12.0 % over the log) | same log, vout 0.6 V rows |

`docs/HANDBOOK.md:181` and `README.md:88` cite `sim/decks/cp_current.spice` as
the source. That deck no longer describes the design: `cp_current.spice:60`
instantiates `tiny_pll_bias_gen`, which `blocks.inc:74`
(`x14 Vdd Vss vbias bias_n bias_p cp_bias`) replaced. Its log is dated
2026-09-12, before both changes.

### 1.4 The loop-filter capacitors

`blocks.inc:359` `XMCAP ... w=4u l=0.6u ng=1 **m=54**` and
`blocks.inc:392` `XMCAP ... w=1.1u l=2u ng=1 **m=9**` — tripled from m=18 / m=3.

Stale: `README.md:88-89` and `docs/HANDBOOK.md:181-182` ("436 fF of loop filter
of which 58 fF is the bypass C2"); `docs/HANDBOOK.md:172-173` ("C1 378 fF",
"C2 58 fF"); `docs/HANDBOOK.md:263-264` ("m = 18 → 378 fF", "m = 3 → 58 fF");
`docs/LAYOUT.md:165` ("a MOS capacitor, `m=18` and `m=3`").

Separately, **436 fF was never what the cited deck measured**:
`sim/results/cp_current.log` reports `c_filt = 5.595340e-13` (559.5 fF) for the
*old* m=18 / m=3 filter. So the figure was the designed sum of the two cells,
presented as a measurement.

`docs/EXPERIMENTS.md:224` ("the 1308 fF filter") is 3 × 436 fF arithmetic, not a
measurement — no deck has measured the tripled filter.

### 1.5 The update quantum

`README.md:90` and `docs/HANDBOOK.md:183` — "**10.1 mV** per bang-bang update".
Both inputs to it moved (pump current halved, filter tripled) and the deck that
produced it has not been re-run since 2026-09-12 15:26.

### 1.6 The two documents disagree with each other about the ring load

- `docs/HANDBOOK.md:240` sizing table: `| R1/R2 load | **7355 Ω** | **9000 Ω** |`
- `docs/RING_DUAL_LOOP.md:403` §7.1: "All 27 corners, at **10000 Ω**"
- `docs/EXPERIMENTS.md:377`: **11 kohm**
- `blocks.inc:450-451`: **10 000 Ω**

Only `RING_DUAL_LOOP.md` matches the netlist. Everything HANDBOOK §10.8 reports
(`:611-639`) was measured at 9000 Ω and is presented as the design's corner
performance: "worst **662.3** at ss/125 °C/1.08 V, **+10.3 %**" (`:613`) and the
slow-end table (`:621-627`), against `RING_DUAL_LOOP.md:403-437`'s 638.2 MHz /
+6.3 % and −5.2 % at the netlist's 10 000 Ω. `docs/HANDBOOK.md:639`
("fast-end margin fell from 15.2 % to 10.3 %") inherits it.

### 1.7 The nominal closed-loop numbers are superseded

`docs/HANDBOOK.md:753` presents as current:
`| tt 27 °C 1.2 V | 600.756 MHz, +0.026 % | 0.599 V | 34.1 mV | e2e_prbs_cpbias.log |`

That is correct for `e2e_prbs_cpbias.log`, but the ripple fixes have since
landed. `sim/results/lowripple.out` (from `e2e_prbs_lr.log`, same deck
`e2e_prbs.spice`):

    f_long = 6.006320e+02    vctrl_s3 = 5.965507e-01    vctrl_ripp = 1.509898e-02

→ 600.632 MHz, 0.597 V, **15.1 mV**. `docs/EXPERIMENTS.md:369-371` has this right;
HANDBOOK does not. The same applies to `docs/HANDBOOK.md:8-11` ("its closed loop
does not lock yet") and `:805` ("667.9 MHz, +11.2 %", measured at 9000 Ω).

### 1.8 Smaller numeric slips

| claim | file:line | actual | evidence |
|---|---|---|---|
| "pump currents **401-458 nA** across corners" | `docs/EXPERIMENTS.md:204` | 392.7-475.5 nA over the log's 27 rows (395.6-457.6 at vout 0.6 V) | `cp_ibias_check.log` |
| "27 corners" for that measurement | `sim/decks/cp_ibias_check.spice:1`, quoted at `docs/EXPERIMENTS.md:150` | 9 T/VDD × 3 vout at **one** process corner — the deck hardwires `.lib ... mos_tt` at line 15 | deck |
| ss/125 C/1.08 V "560.0 MHz, -6.8 %", vctrl "0.580 -> 0.588 V", "Re-running seeded at 0.85 V" | `docs/EXPERIMENTS.md:394-397` | the re-run finished: **564.95 MHz, −5.94 %**, 0.588 → 0.593 V | `sim/results/run_dual_ss125_108.out`: `f_long = 5.649520e+02`, `f_err = -5.93540e+00`, `vctrl_e1 = 5.880130e-01`, `vctrl_e2 = 5.931874e-01` |
| mismatch "**6.7 %**" | `README.md:278`, `docs/DESIGN.md:431`, `docs/PROPOSAL.md:198` | −7.8 % now; `docs/HANDBOOK.md:860` already flags this one as wrong | `cp_ibias_check.log` |

### 1.9 Counts and area

`python3 tools/area_budget.py` on the current netlist:

    cap_cmomf   3   2132.9 um2
    rhigh      44    491.4
    sg13_lv_nmos 149 578.5
    sg13_lv_pmos  69  97.9
    total      265   3300.6

| claim | file:line | actual |
|---|---|---|
| "**268 devices, 3094 µm²**" | `docs/HANDBOOK.md:639` | 265 devices, 3300.6 µm² |
| "3094 µm² — about **2 %** of the slot" | `docs/HANDBOOK.md:958`, `docs/CHIPALOOZA_SLOT.md:27`, `docs/LAYOUT.md:311` | 3300.6 µm², 2.25 % of 146 642 µm² |
| "225 devices / 2131 µm²", 136/45/43/1 breakdown | `README.md:190-192` | 265 / 3300.6 |
| "The sky130 design flattened to 224 devices; the extra one is the bias mirror" | `README.md:196` | four native cells have been added since |
| "**43** `rhigh` instances" | `docs/LAYOUT.md:209` | 44 |
| "**46** long poly resistors" | `docs/CHIPALOOZA_SLOT.md:29` | 44 |
| "1243 µm² ... **more than half** the drawn device area" | `docs/LAYOUT.md:204-206` | 1243 / 3300.6 = 37.7 %; all three `cap_cmomf` together are 65 % (which is what `area_budget.py` now prints) |
| "the design — **24 cells**" | `CLAUDE.md:103` | 27 `.sch`, 26 `.sym`, 24 `.subckt` in `blocks.inc` |
| "the design — **25 schematics**" | `docs/HANDBOOK.md:982` | 27 |
| "**Two** cells are native ... `inv_cp` and `ibias_mirror`" | `CLAUDE.md:73-75` | five: + `coarse_loop`, `sb_inverter`, `cp_bias` (`tools/gen_coarse_loop.py:52-64`) |
| "The **three** native cells are `inv_cp`, `ibias_mirror` and `coarse_loop`" | `docs/HANDBOOK.md:75-77` | five |
| "`test/` holds **48** tests" | `docs/HANDBOOK.md:341`, `:870`; `tools/run_checks.py:101` | **49** (§5 below) |
| "All 22 cells translated ... 21 subcircuits, 121 instances" | `README.md:29` | pre-branch; `blocks.inc` now has 24 `.subckt` |
| "Coarse tuning ... is specified but **not built**" / "8 of 27 corners" | `README.md:32`, `:159`, `:271-274` | built and in the netlist (`blocks.inc:72`, `:252-298`); `RING_DUAL_LOOP.md:403-437` brackets all 27 at 10 000 Ω |
| "**Not measured**: ... no PRBS" | `README.md:33` | PRBS7 has run at several corners (`e2e_prbs_*.log`) |

### 1.10 Structural claims that are now wrong

- `docs/HANDBOOK.md:340` says `test_hierarchy.py` prevents "a cell that is
  defined but never instantiated, or vice versa". It does not — see §3.3.
  Live consequence: `xschem/tiny_pll_bias_gen.{sch,sym}` and
  `xschem/tiny_pll_bias_gen_res.{sch,sym}` are no longer instantiated anywhere
  (absent from `blocks.inc`) and nothing flags them.
- `docs/LAYOUT.md:175-183` Tier-2 composition still reads
  `CDR = phase detector + pump + bias gen + filter + ring + diff_amp_inv +
  buffers + precharge`. `blocks.inc:64-74` also has `coarse_loop` (x30),
  `sb_inverter` (x13) and `cp_bias` (x14), and no `tiny_pll_bias_gen`.
  `docs/LAYOUT.md:167` still lists `tiny_pll_bias_gen_res` as a cell to lay out.
- `docs/RING_COARSE_TUNE.md` in whole describes the switchable-resistor-leg
  candidate that `docs/HANDBOOK.md:441-454` records as rejected in favour of the
  analog loop. Its numbers (8002 Ω states, "225 devices to about 265",
  `fsel0b`/`fsel1b` pins) describe nothing in the netlist. It is a design note,
  but nothing in it says it lost.

---

## 2. `tools/run_checks.py` — what breaks, what passes vacuously

Six of the eleven stages have a problem. Every bound below is the value the
named log actually contains.

### 2.1 `cp-current` (`tools/run_checks.py:153-161`) — wrong circuit, and no checks at all

Two faults. The deck is stale: `sim/decks/cp_current.spice:60` instantiates
`tiny_pll_bias_gen`, replaced in the design by `cp_bias` (`blocks.inc:74`). And
the stage carries **no `checks` list**, so it passes on `safe_ngspice` exit
status alone — the one stage whose entire subject matter (pump current, filter
capacitance, mismatch) was changed in the last day cannot fail. Its description
also states the stale "11.0 % up/down mismatch".

Proposed: point the deck's bias at `cp_bias` from a 40 µA `ibias_mirror`, the
way `sim/decks/cp_ibias_check.spice:22-24` already does, then add

| check | low | high | unit | justified by |
|---|---|---|---|---|
| `i_up` | 3.9e-7 | 4.6e-7 | A | `cp_ibias_check.log`: 416.3 nA nominal, 392.7-437.9 nA over 27 rows |
| `i_down` | -4.9e-7 | -4.1e-7 | A | same log: 450.2 nA nominal, 416.1-475.5 nA |
| `i_leak` | 0.0 | 1e-10 | A | `cp_current.log`: `i_leak = 1.971529e-11` |
| `c_filt` | 1.5e-12 | 1.9e-12 | F | `cp_current.log` measured `c_filt = 5.595340e-13` for m=18/m=3; `blocks.inc:359,392` are now m=54/m=9, i.e. 3× ⇒ ~1.68 pF. **Re-run the deck and pin the bound to what it reports** — do not carry the docs' 436 fF, which that log never supported. |

### 2.2 `e2e-lock` (`:202-221`) — the `known_broken` string now hides real failures

`known_broken` says "On ring-coarse-tune this reaches 667.9 MHz, +11.2 %, with
vctrl climbing". That was the 9000 Ω ring. At the netlist's 10 000 Ω with
`sb_inverter` + `cp_bias` + the ripple fixes, nominal locks
(`docs/HANDBOOK.md:777`: 0101 at 600.554 MHz; `lowripple.out`: PRBS7 at
600.632 MHz). Because `run_stage` (`:345-346`) demotes any failure of a stage
with a non-empty `known_broken` to `known-fail` and `main` (`:439`) returns 0 on
those, **a genuine new regression in the headline stage exits zero**. This is the
most dangerous single line in the file.

Proposed: delete `known_broken`, and

| check | low | high | unit | justified by |
|---|---|---|---|---|
| `f_long` | 599.0 | 602.0 | MHz | `docs/HANDBOOK.md:777` 0101 at 600.554 MHz on this ring |
| `f_err` | -0.3 | 0.3 | % | same |
| `vctrl_ripp` | 0.0 | 0.025 | V | `lowripple.out` `vctrl_ripp = 1.509898e-02` on **PRBS7**; 0101 is always quieter, so 25 mV is a ceiling with margin. The current 0.045 now passes vacuously. |
| `rclk_swing` | 1.0 | 1.45 | V | `lowripple.out` 1.306926 nominal, 1.418099 at ff/-40 C |

Also flag: the deck is a 1500 ns transient (`e2e_lock.spice:120`) and
`docs/EXPERIMENTS.md:214` records that acquisition is now **~5× slower**. The
stage may start failing purely because the window no longer contains a lock.
Lengthen the transient, and bound the drift the deck already measures
(`e2e_lock.spice:131-132`, `vctrl_e1`/`vctrl_e2`) at |e2−e1| ≤ 5 mV rather than
relying on ripple alone.

### 2.3 `e2e-prbs` (`:222-234`) — same `known_broken`, and a vacuous ripple bound

`known_broken="Same cause as e2e-lock on this branch."` — same problem as 2.2.
`vctrl_ripp` is bounded 0.0-0.10 V with the note "65.3 mV on the old ring";
measured now is **15.1 mV** (`lowripple.out`), so the bound is ~6.6× the value
and cannot fail. The stage also has **no `rclk_swing` check**, although PRBS7 at
125 °C is exactly where the clock died (`docs/HANDBOOK.md:641-661`).

Proposed:

| check | low | high | unit | justified by |
|---|---|---|---|---|
| `f_long` | 599.0 | 602.0 | MHz | `lowripple.out` `f_long = 6.006320e+02` |
| `f_err` | -0.3 | 0.3 | % | `f_err = 5.334085e-03` |
| `vctrl_ripp` | 0.0 | 0.025 | V | `vctrl_ripp = 1.509898e-02` |
| `rclk_swing` | 1.0 | 1.45 | V | `rclk_swing = 1.306926e+00` |
| `vctrl_s3` | 0.58 | 0.62 | V | `vctrl_s3 = 5.965507e-01`; catches the drift case that ripple cannot |

The deck itself (`e2e_prbs.spice`) is current — `lowripple.out` came from it.

### 2.4 `vco-rsweep` (`:162-169`) — measures a ring that is not the design

`sim/decks/vco_rsweep.spice:25` includes `ring_p.inc`, whose
`.param Win=3 Lin=1.0` / `.param Rload=7355` (`ring_p.inc:33,35`) is **main's**
ring — no trim leg, 1.0 µm pair. The branch's ring is 0.7 µm / 10 000 Ω with a
4 µm trim leg (`blocks.inc:447-453`). `sim/results/vco_rsweep.log` confirms it:
`p_rload = 7.355000e+03` → `fosc = 6.036634e+08`, which is main's 603.7 MHz.
The stage also has **no checks**.

Proposed: either retire the stage, or repoint it at `ring_ct.inc` (the include
`apply_ring_sizing.py:58-61` keeps in step with the design) and add

| check | low | high | unit | justified by |
|---|---|---|---|---|
| `f_trimoff_nom` | 460 | 500 | MHz | `docs/RING_DUAL_LOOP.md:418` trim-off tt/27 °C/1.20 V = 480.5 MHz at 10 000 Ω |

The "61.0 ps + 13.100 ps per kilohm" in the description is a main-ring fit and
should be re-stated or dropped.

### 2.5 `vco-ct-centre` (`:185-193`) — correct deck, no checks, and the parser cannot see the sweep

The deck is current (`vco_ct_centre.spice:26` includes `ring_ct.inc`, which is at
`Rload=10000` / `Wtr=4`, matching `blocks.inc`). But the stage has no checks, and
adding a naive one would not work: `read_measures` (`:245-262`) is **last-wins**,
and the deck prints `fosc`/`swing`/`p_vcrs`/`p_vctrl` once per sweep row, so a
`Check("fosc", ...)` would silently bound only the final row
(`p_vcrs = 0.15`, `p_vctrl = 0.70`, `fosc = 7.947637e+08`).

Proposed: have the deck emit uniquely-named summary `let`s, then

| check | low | high | unit | justified by |
|---|---|---|---|---|
| `f_vcrs120_vctrl060` | 460 | 500 | MHz | `docs/RING_DUAL_LOOP.md:418` trim off, tt/27/1.20 = 480.5 MHz |
| `f_vcrs000_vctrl120` | 815 | 865 | MHz | `docs/RING_DUAL_LOOP.md:411` trim on, tt/27/1.20 = 840.7 MHz |

### 2.6 `trim-r` (`:142-152`) — passes tautologically, and against the wrong resistance

`r_alone` is the bare reference resistor solved from `.param Rload=8000`
(`trim_r.spice:30-35`) and measured back: `sim/results/trim_r.log`
`r_alone = -8.00006e+03`. It re-confirms the deck's own arithmetic and can only
fail if the PDK's resistance model changes. Meanwhile 8000 Ω is not any
resistance in the design — the ring load is 10 000 Ω (`blocks.inc:450`) — and the
stage's real subject, the trim leg's effectiveness, is **not checked**: the
`reff` sweep prints 45 rows and last-wins leaves only `reff = -1.80101e+03`
(the W = 8 µm, Vg = 0 row), which is not the adopted 4 µm leg.

Proposed: set `.param Rload=10000` to match the design, keep `r_alone` as an
arithmetic canary at **[-1.05e4, -9.5e3]**, and add a uniquely-named summary for
the adopted width:

| check | low | high | unit | justified by |
|---|---|---|---|---|
| `reff_w4_vg0` | -3.1e3 | -2.7e3 | ohm | `trim_r.log`, `w_um = 4` / `vg_v = 0` row: `reff = -2.89368e+03` (at the present 8000 Ω reference; re-measure after the Rload change) |

### 2.7 `repo-tests` (`:99-106`) — description says 48, pytest says 49

Cosmetic but it lands in `sim/results/CHECKS.md` as a fact. See §5.

### 2.8 `toolchain` (`:107-114`) — passes, but misses the failure that actually happened

It compares `blocks.inc`'s mtime against the schematics and is currently green
(`blocks.inc` 23:50:28 vs newest `.sch` 23:50:27). It cannot catch §1.1, where
the *intended* sizing in `tools/port_from_sky130.py` and `sim/decks/ring_ct.inc`
was never applied, so the netlist is self-consistent and wrong.

Proposed addition (no bound needed, it is an equality): solve
`("ring_inverter","R1")["R"]` from `tools/port_from_sky130.py:236` and
`.param Rload` from `sim/decks/ring_ct.inc:105` through the same
`Lload` expression, and require both to reproduce `blocks.inc`'s
`XR1 ... l=` to 1 part in 10⁵. Today: 10 000 / 10 000 / `l=6.945882e-06` — agree.
Had the 11 kΩ apply half-completed, this would have named it.

### 2.9 Unchanged and still valid

`char-caps` (`:116-128`) and `cap-leak` (`:129-141`) measure PDK passives and are
untouched by any of these changes; their bounds still bracket
`sim/results/char_caps.log` and `cap_leak.log`. `coarse-tb` (`:170-184`) runs
`coarse_tb.spice`, which includes `coarse_loop.inc` — the adopted folded cell,
37 devices, matching `blocks.inc:261-297` — and all four checks pass on
`sim/results/coarse_tb.log` (`v_park = 1.201544e+00`,
`search_mv_us = 1.895583e+01`, `search_span = 1.078399e+00`,
`d_600 = 1.858214e-02`). Two notes:

- the bounds are much looser than the measurement warrants. Tighter, from that
  same log: `v_park` [1.15, 1.25], `search_mv_us` [17.0, 21.0],
  `search_span` [1.03, 1.13], `d_600` [-0.15, 0.15].
- the `d_600` note "the null sits at vctrl = 0.600 V, **against a locked
  0.599 V**" is stale: nominal lock is now 0.597 V
  (`lowripple.out` `vctrl_s1 = 5.969908e-01`).

`ctle-ac` (`:195-201`) is unaffected (the CTLE was not touched) but likewise has
no numeric checks — it passes on the shell script's exit status.

---

## 3. `test/` — coverage gaps for the new native cells

### 3.1 There is nothing equivalent to `test_coarse_loop.py` for `sb_inverter` or `cp_bias`

`grep -rn "sb_inverter\|cp_bias" test/` returns **nothing**. Both cells are in the
design (`blocks.inc:301-313`, `:316-329`) and both are generated
(`tools/gen_coarse_loop.py:52-64`), and neither has any test.

### 3.2 The generated-vs-include check is hard-coded to `coarse_loop`, not generic

`test/test_coarse_loop.py:32-34` pins the paths —

    INC = ROOT / "sim" / "decks" / "coarse_loop.inc"
    SCH = ROOT / "xschem" / "coarse_loop.sch"
    SYM = ROOT / "xschem" / "coarse_loop.sym"

— and `test_schematic_is_up_to_date` (`:70-85`) invokes the generator with
`--inc <coarse_loop.inc>` rather than `--cell`, reading back
`Path(d) / "coarse_loop.sch"`. All seven tests in the file are single-cell. The
generator already knows all three cells in its `CELLS` dict
(`tools/gen_coarse_loop.py:52-64`), so parameterising the file over
`gen_coarse_loop.CELLS` would cover `sb_inverter` and `cp_bias` at no design
cost, and would extend automatically to the next native cell.

Per-test, what each one would newly cover:

| test | applies to the new cells? |
|---|---|
| `test_files_exist` (`:66`) | yes, trivially |
| `test_schematic_is_up_to_date` (`:70`) | **the important one** — §4 shows both cells are in sync today, but nothing enforces it |
| `test_every_pin_is_labelled` (`:87`) | yes — `sb_inverter`'s `XCC`/`XRFB` and `cp_bias`'s four devices are label-connected exactly like `coarse_loop`'s |
| `test_only_manufacturable_devices` (`:97`) | `sb_inverter` uses `cap_cmomf` and `rhigh`; already in the allowed set, worth pinning |
| `test_no_moscap` (`:103`) | `sb_inverter`'s coupling cap is the one place a `moscap` swap would be tempting (12.7 vs 1.29 fF/µm²) and would be silently non-linear |
| `test_ksweep_is_one` (`:109`) | `coarse_loop`-specific; no analogue needed |
| `test_netlist_matches_include` (`:119`) | yes — the terminal-by-terminal check, which is what catches an xschem coordinate error |

### 3.3 Nothing tests the two new `POST_PORT_EDITS`

`tools/port_from_sky130.py:969-972` composes three edits into `CDR.sch`:

    "CDR.sch": lambda t: replace_bias_gen(add_sb_clock_stage(add_coarse_loop(t))),

`test/test_port_tool.py:202-213` has `test_coarse_loop_is_instantiated_in_the_cdr`,
which calls `add_coarse_loop` and asserts each pin lands on the right net at the
right offset. There is **no equivalent for `add_sb_clock_stage`
(`port_from_sky130.py:909`) or `replace_bias_gen` (`:942`)**. Both are exactly
the class of edit the coarse-loop test exists to police — xschem connects by
coordinate, and `sb_inverter` is deliberately fed from `clkraw−` rather than
`clkraw+` (`blocks.inc:73`) because the inversion has to restore the polarity at
`rclk+`. A pin swapped there would flip the Alexander detector's data and edge
samplers and still netlist and simulate.

### 3.4 Missing hierarchy assertions

`test/test_hierarchy.py:67-72` (`test_cdr_contains_its_loop`) checks for
`alexander_phase_detector`, `tiny_pll_charge_pump`, `tiny_pll_loop_filter`,
`ring_oscillator` and `vctrl_precharge` in `CDR.sch`. It does **not** check for
`coarse_loop.sym`, `sb_inverter.sym` or `cp_bias.sym`, and it does not assert
that `tiny_pll_bias_gen.sym` is *gone* — so a `replace_bias_gen` that silently
no-ops would leave the old generator in the loop and every test would pass.

There is also no "defined but never instantiated" test, despite
`docs/HANDBOOK.md:340` claiming one, which is why the now-dead
`tiny_pll_bias_gen.{sch,sym}` and `tiny_pll_bias_gen_res.{sch,sym}` sit in
`xschem/` unflagged.

### 3.5 No geometry/device-set gap

`test_device_set.py` and `test_device_geometry.py` both glob `xschem/*.sch`, so
they already cover `sb_inverter.sch` and `cp_bias.sch` generically. Note that
`cp_bias`'s `XMN1` at L = 8 µm (`blocks.inc:325`) sits close to PSP's 10 µm
ceiling — `docs/EXPERIMENTS.md:202` records that the L = 16 µm variant was
rejected by exactly this test, which is the system working.

---

## 4. Do the native cells regenerate identically?

`python3 tools/gen_coarse_loop.py --cell <cell> --out /tmp/genchk`, diffed
against `xschem/<cell>.sch`. Nothing was written into `xschem/`.

| cell | generator output | diff vs `xschem/<cell>.sch` |
|---|---|---|
| `coarse_loop` | `coarse_loop.sch: 37 devices, ports VDD VSS ibias vctrl vcoarse` | **identical** |
| `sb_inverter` | `sb_inverter.sch: 4 devices, ports VDD VSS in out` | **identical** |
| `cp_bias` | `cp_bias.sch: 4 devices, ports VDD VSS vbias bias_n bias_p` | **identical** |

All three are in sync with their includes. Device counts and ports agree with
`blocks.inc:252-329`.

One usability note: the tool does not create `--out` if it is missing — it fails
with `FileNotFoundError: .../coarse_loop.sch` from `pathlib.write_text`. The
directory has to be `mkdir -p`'d first. `test_coarse_loop.py:73` happens to avoid
this by using `tempfile.TemporaryDirectory()`.

---

## 5. `python3 -m pytest -q test/`

    .................................................                        [100%]
    49 passed in 0.52s

Green. The count is **49**, not the 48 stated at `docs/HANDBOOK.md:341`,
`docs/HANDBOOK.md:870` and `tools/run_checks.py:101` (which propagates into
`sim/results/CHECKS.md`).

// MSK12C02 side-actuated SPDT slide switch (same part/footprint as the Sweep 2 and
// the SplitKB Wireless Controller Expansion Bundle), lever toward local -y.
// reversible: pads on both faces, mirrored, so the switch can sit on the top face
// of either half. Mechanical NPTH pegs are shared.
// Nets: from = battery side, to = pin 2 (common, to the XIAO). The battery is on pin 1
// on F and on pin 3 on B, i.e. on the pad at the same board position on both faces, so
// ON is the same lever direction (toward local +x) on both halves.
module.exports = {
  params: { designator: 'SW', reversible: true, from: undefined, to: undefined },
  body: p => {
    // m = 1: battery on pin 1; m = -1 (mirrored part on B): battery on pin 3
    const face = (s, m) => `
      (pad 1 smd rect (at ${m * 2.25} 2.075 ${p.r}) (size 0.9 1.25) (layers ${s}.Cu ${s}.Paste ${s}.Mask) ${m > 0 ? p.from : ''})
      (pad 2 smd rect (at ${m * -0.75} 2.075 ${p.r}) (size 0.9 1.25) (layers ${s}.Cu ${s}.Paste ${s}.Mask) ${p.to})
      (pad 3 smd rect (at ${m * -2.25} 2.075 ${p.r}) (size 0.9 1.25) (layers ${s}.Cu ${s}.Paste ${s}.Mask) ${m > 0 ? '' : p.from})
      (pad "" smd rect (at 3.7 -1.1 ${p.r}) (size 0.9 0.9) (layers ${s}.Cu ${s}.Paste ${s}.Mask))
      (pad "" smd rect (at 3.7 1.1 ${p.r}) (size 0.9 0.9) (layers ${s}.Cu ${s}.Paste ${s}.Mask))
      (pad "" smd rect (at -3.7 1.1 ${p.r}) (size 0.9 0.9) (layers ${s}.Cu ${s}.Paste ${s}.Mask))
      (pad "" smd rect (at -3.7 -1.1 ${p.r}) (size 0.9 0.9) (layers ${s}.Cu ${s}.Paste ${s}.Mask))
      (fp_line (start -3.3 -1.35) (end 3.3 -1.35) (layer ${s}.SilkS) (width 0.12))
      (fp_line (start -3.3 1.5) (end -1.4 1.5) (layer ${s}.SilkS) (width 0.12))
      (fp_line (start 3.3 1.5) (end 2.9 1.5) (layer ${s}.SilkS) (width 0.12))`
    return `
    (module MSK12C02_REV (layer F.Cu) (tedit 0)
      ${p.at}
      (fp_text reference "${p.ref}" (at 0 4 ${p.r}) (layer F.SilkS) ${p.ref_hide} (effects (font (size 1 1) (thickness 0.15))))
      (fp_line (start -1.95 -3.85) (end 1.95 -3.85) (layer Dwgs.User) (width 0.15))
      (fp_line (start 1.95 -3.85) (end 1.95 -1.35) (layer Dwgs.User) (width 0.15))
      (fp_line (start -1.95 -1.35) (end -1.95 -3.85) (layer Dwgs.User) (width 0.15))
      (pad "" np_thru_hole circle (at 1.5 0) (size 0.9 0.9) (drill 0.9) (layers *.Cu *.Mask))
      (pad "" np_thru_hole circle (at -1.5 0) (size 0.9 0.9) (drill 0.9) (layers *.Cu *.Mask))
      ${face('F', 1)}
      ${p.reversible ? face('B', -1) : ''}
    )
    `
  }
}

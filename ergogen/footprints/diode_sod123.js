// SOD-123 signal diode (1N4148W), hand-solderable pads.
// reversible: identical pads on both faces (populate the bottom face of each half).
// from = anode, to = cathode (bar), matching ZMK/QMK col2row with the switch
// between column and anode.
module.exports = {
  params: { designator: 'D', side: 'B', reversible: false, from: undefined, to: undefined },
  body: p => {
    if (p.reversible) {
      const b = module.exports.body({ ...p, reversible: false, side: 'B' })
      const f = module.exports.body({ ...p, reversible: false, side: 'F', ref_hide: 'hide' })
      return merge(b, f)
    }
    const s = p.side
    const mirror = s == 'B' ? '(justify mirror)' : ''
    return `
    (module D_SOD-123 (layer ${s}.Cu) (tedit 0)
      ${p.at}
      (fp_text reference "${p.ref}" (at 0 1.6 ${p.r}) (layer ${s}.SilkS) ${p.ref_hide} (effects (font (size 0.8 0.8) (thickness 0.12)) ${mirror}))
      (fp_text value "1N4148W" (at 0 -1.6 ${p.r}) (layer ${s}.Fab) (effects (font (size 0.8 0.8) (thickness 0.12)) ${mirror}))
      (fp_line (start -2.35 -1) (end -2.35 1) (layer ${s}.SilkS) (width 0.15))
      (fp_line (start -2.35 -1) (end 1.4 -1) (layer ${s}.SilkS) (width 0.12))
      (fp_line (start -2.35 1) (end 1.4 1) (layer ${s}.SilkS) (width 0.12))
      (fp_line (start -0.35 0) (end 0.25 -0.4) (layer ${s}.SilkS) (width 0.1))
      (fp_line (start 0.25 -0.4) (end 0.25 0.4) (layer ${s}.SilkS) (width 0.1))
      (fp_line (start 0.25 0.4) (end -0.35 0) (layer ${s}.SilkS) (width 0.1))
      (fp_line (start -0.35 -0.5) (end -0.35 0.5) (layer ${s}.SilkS) (width 0.1))
      (fp_line (start -2.6 -1.2) (end 2.6 -1.2) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start 2.6 -1.2) (end 2.6 1.2) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start 2.6 1.2) (end -2.6 1.2) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start -2.6 1.2) (end -2.6 -1.2) (layer ${s}.CrtYd) (width 0.05))
      (pad 1 smd roundrect (at -1.65 0 ${p.r}) (size 1.1 1.3) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2) ${p.to})
      (pad 2 smd roundrect (at 1.65 0 ${p.r}) (size 1.1 1.3) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2) ${p.from})
    )
    `
  }
}

// combine two single-sided bodies into one module: keep the first header, append
// the second's pads/graphics (everything after its "at" line)
function merge(a, b) {
  const inner = b.slice(b.indexOf('\n', b.indexOf('(at ')) + 1, b.lastIndexOf(')'))
  return a.slice(0, a.lastIndexOf(')')) + inner.replace(/\(fp_text reference[^\n]*\n/, '') + ')\n'
}

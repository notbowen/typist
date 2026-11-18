// JST SH 1.0 mm 2-pin, SMD side entry (SM02B-SRSS-TB), for the LiPo cell.
// Body 4.0 x 4.25 x 2.95 mm, centred on the origin. Cable enters from local -y.
// Pad geometry is KiCad's JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal rotated
// 180 deg (pins 0.325 mm behind the body, anchor tabs at x = +-1.8, 3.875 mm from the
// pin row). Pin 1 = BAT+, pin 2 = GND
// (the common "Adafruit" polarity - cheap cells are often reversed: CHECK).
// reversible: pads on both faces, pin 1 mirrored so the housing fits either face.
module.exports = {
  params: { designator: 'J', side: 'B', reversible: false, pos: undefined, neg: undefined },
  body: p => {
    if (p.reversible) {
      const b = module.exports.body({ ...p, reversible: false, side: 'B' })
      const f = module.exports.body({ ...p, reversible: false, side: 'F', ref_hide: 'hide' })
      return merge(b, f)
    }
    const s = p.side
    const mirror = s == 'B' ? '(justify mirror)' : ''
    const fx = s == 'B' ? -1 : 1       // keep pin 1 on the same physical side when flipped
    return `
    (module JST_SH_SM02B-SRSS-TB (layer ${s}.Cu) (tedit 0)
      ${p.at}
      (fp_text reference "${p.ref}" (at 0 3.6 ${p.r}) (layer ${s}.SilkS) ${p.ref_hide} (effects (font (size 0.8 0.8) (thickness 0.12)) ${mirror}))
      (fp_text value "SM02B-SRSS-TB" (at 0 5 ${p.r}) (layer ${s}.Fab) (effects (font (size 0.8 0.8) (thickness 0.12)) ${mirror}))
      (fp_text user "+" (at ${fx * -1.6} 2.45 ${p.r}) (layer ${s}.SilkS) (effects (font (size 1 1) (thickness 0.15)) ${mirror}))
      (fp_text user "-" (at ${fx * 1.6} 2.45 ${p.r}) (layer ${s}.SilkS) (effects (font (size 1 1) (thickness 0.15)) ${mirror}))
      (fp_line (start -2 -2.125) (end 2 -2.125) (layer ${s}.Fab) (width 0.1))
      (fp_line (start 2 -2.125) (end 2 2.125) (layer ${s}.Fab) (width 0.1))
      (fp_line (start 2 2.125) (end -2 2.125) (layer ${s}.Fab) (width 0.1))
      (fp_line (start -2 2.125) (end -2 -2.125) (layer ${s}.Fab) (width 0.1))
      (fp_line (start -2.15 0.1) (end -2.15 1.6) (layer ${s}.SilkS) (width 0.12))
      (fp_line (start 2.15 0.1) (end 2.15 1.6) (layer ${s}.SilkS) (width 0.12))
      (fp_line (start -2.9 -2.9) (end 2.9 -2.9) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start 2.9 -2.9) (end 2.9 3.4) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start 2.9 3.4) (end -2.9 3.4) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start -2.9 3.4) (end -2.9 -2.9) (layer ${s}.CrtYd) (width 0.05))
      (pad 1 smd roundrect (at ${fx * -0.5} 2.45 ${p.r}) (size 0.6 1.55) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2) ${p.pos})
      (pad 2 smd roundrect (at ${fx * 0.5} 2.45 ${p.r}) (size 0.6 1.55) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2) ${p.neg})
      (pad "" smd roundrect (at -1.8 -1.425 ${p.r}) (size 1.2 1.8) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2))
      (pad "" smd roundrect (at 1.8 -1.425 ${p.r}) (size 1.2 1.8) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2))
    )
    `
  }
}

function merge(a, b) {
  const inner = b.slice(b.indexOf('\n', b.indexOf('(at ')) + 1, b.lastIndexOf(')'))
  return a.slice(0, a.lastIndexOf(')')) + inner.replace(/\(fp_text reference[^\n]*\n/, '') + ')\n'
}

// JST SH 1.0 mm 2-pin, SMD side entry (SM02B-SRSS-TB), for the LiPo cell.
// Body 6.0 x 4.25 x 2.95 mm. Cable enters from local -y. Pin 1 = BAT+, pin 2 = GND
// (the common "Adafruit" polarity - cheap cells are often reversed: CHECK).
module.exports = {
  params: { designator: 'J', side: 'B', pos: undefined, neg: undefined },
  body: p => {
    const s = p.side
    const mirror = s == 'B' ? '(justify mirror)' : ''
    const fx = s == 'B' ? -1 : 1       // keep pin 1 on the same physical side when flipped
    return `
    (module JST_SH_SM02B-SRSS-TB (layer ${s}.Cu) (tedit 0)
      ${p.at}
      (fp_text reference "${p.ref}" (at 0 3.6 ${p.r}) (layer ${s}.SilkS) ${p.ref_hide} (effects (font (size 0.8 0.8) (thickness 0.12)) ${mirror}))
      (fp_text value "SM02B-SRSS-TB" (at 0 5 ${p.r}) (layer ${s}.Fab) (effects (font (size 0.8 0.8) (thickness 0.12)) ${mirror}))
      (fp_text user "+" (at ${fx * -0.5} -3.1 ${p.r}) (layer ${s}.SilkS) (effects (font (size 1 1) (thickness 0.15)) ${mirror}))
      (fp_text user "-" (at ${fx * 1.5} -3.1 ${p.r}) (layer ${s}.SilkS) (effects (font (size 1 1) (thickness 0.15)) ${mirror}))
      (fp_line (start -3 -2.1) (end 3 -2.1) (layer ${s}.Fab) (width 0.1))
      (fp_line (start 3 -2.1) (end 3 2.15) (layer ${s}.Fab) (width 0.1))
      (fp_line (start 3 2.15) (end -3 2.15) (layer ${s}.Fab) (width 0.1))
      (fp_line (start -3 2.15) (end -3 -2.1) (layer ${s}.Fab) (width 0.1))
      (fp_line (start -3.1 -1.0) (end -3.1 0.2) (layer ${s}.SilkS) (width 0.12))
      (fp_line (start 3.1 -1.0) (end 3.1 0.2) (layer ${s}.SilkS) (width 0.12))
      (fp_line (start -3.9 -2.6) (end 3.9 -2.6) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start 3.9 -2.6) (end 3.9 2.9) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start 3.9 2.9) (end -3.9 2.9) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start -3.9 2.9) (end -3.9 -2.6) (layer ${s}.CrtYd) (width 0.05))
      (pad 1 smd roundrect (at ${fx * -0.5} 1.775 ${p.r}) (size 0.6 1.55) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2) ${p.pos})
      (pad 2 smd roundrect (at ${fx * 0.5} 1.775 ${p.r}) (size 0.6 1.55) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2) ${p.neg})
      (pad "" smd roundrect (at -2.3 -1.2 ${p.r}) (size 1.2 1.8) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2))
      (pad "" smd roundrect (at 2.3 -1.2 ${p.r}) (size 1.2 1.8) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2))
    )
    `
  }
}

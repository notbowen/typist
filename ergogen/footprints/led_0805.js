// 0805 status LED + 0805 series resistor as one footprint (GPIO -> R -> LED -> GND).
// reversible: identical pads on both faces; populate the face that is up for that
// half. Layout (local, y down): resistor at y=-1.6, LED at y=+1.6, both along x.
//   R:   pad1 (-1.0,-1.6) = gpio      pad2 (1.0,-1.6) = mid (to LED anode)
//   LED: anode (1.0, 1.6) = mid       cathode (-1.0, 1.6) = GND  (bar on silk)
// Nets: gpio, gnd (the R-LED node is local)
module.exports = {
  params: { designator: 'LED', reversible: true, gpio: undefined, gnd: undefined, mid: undefined },
  body: p => {
    const face = (s) => {
      const mir = s == 'B' ? '(justify mirror)' : ''
      return `
      (pad 1 smd roundrect (at -1.0 -1.6 ${p.r}) (size 1.0 1.3) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2) ${p.gpio})
      (pad 2 smd roundrect (at 1.0 -1.6 ${p.r}) (size 1.0 1.3) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2) ${p.mid})
      (pad 3 smd roundrect (at 1.0 1.6 ${p.r}) (size 1.0 1.3) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2) ${p.mid})
      (pad 4 smd roundrect (at -1.0 1.6 ${p.r}) (size 1.0 1.3) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.2) ${p.gnd})
      (fp_line (start -1.95 0.85) (end -1.95 2.35) (layer ${s}.SilkS) (width 0.2))
      (fp_text user "R" (at 2.2 -1.6 ${p.r}) (layer ${s}.SilkS) (effects (font (size 0.6 0.6) (thickness 0.1)) ${mir}))
      (fp_line (start -1.75 -2.5) (end 1.75 -2.5) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start 1.75 -2.5) (end 1.75 2.5) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start 1.75 2.5) (end -1.75 2.5) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start -1.75 2.5) (end -1.75 -2.5) (layer ${s}.CrtYd) (width 0.05))`
    }
    return `
    (module LED_0805_R_0805_REV (layer F.Cu) (tedit 0)
      ${p.at}
      (fp_text reference "${p.ref}" (at 0 3.4 ${p.r}) (layer F.SilkS) hide (effects (font (size 0.8 0.8) (thickness 0.12))))
      ${face('F')}
      ${p.reversible ? face('B') : ''}
    )
    `
  }
}

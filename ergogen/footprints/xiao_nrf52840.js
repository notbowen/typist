// Seeed Studio XIAO nRF52840 (also XIAO nRF52840 Sense / Plus), surface mounted
// flat via its castellated edge pads, USB-C toward local -y.
//
// reversible: true -> one PCB for both halves. The XIAO always sits on the face
// that is "up" for that half (F on the left half, B on the flipped right half), so
// every XIAO pin gets a pad on F at its normal spot AND a pad on B at the mirrored
// spot, both on the same net. Same XIAO pin = same signal on both halves, so the
// firmware pin map is identical. Pads that share an x/y on opposite faces carry
// different signals; they are SMD, never joined by a via.
//
// Underside pads reached by plated through-holes (solder from the other face):
//   BAT- (-4.445,-2.2225)  BAT+ (-4.445,-0.3175)  P0.09/NFC1 (3.81,9.2075)  P0.10/NFC2 (5.715,9.2075)
// (pad positions cross-checked against ebastler/marbastlib and amacleod/weejock)
//
// Nets: D0..D10, V5, GND, V3, BATP, BATN, NFC1, NFC2
module.exports = {
  params: {
    designator: 'MCU', reversible: false,
    D0: undefined, D1: undefined, D2: undefined, D3: undefined, D4: undefined,
    D5: undefined, D6: undefined, D7: undefined, D8: undefined, D9: undefined,
    D10: undefined, V5: undefined, GND: undefined, V3: undefined,
    BATP: undefined, BATN: undefined, NFC1: undefined, NFC2: undefined,
  },
  body: p => {
    const left = [p.D0, p.D1, p.D2, p.D3, p.D4, p.D5, p.D6]
    const right = [p.V5, p.GND, p.V3, p.D10, p.D9, p.D8, p.D7]
    const lname = ['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6']
    const rname = ['5V', 'G', '3V3', 'D10', 'D9', 'D8', 'D7']
    // pad: 1.9 mm long, reaching 0.4 mm past the XIAO edge (8.89) for the fillet
    const PX = 8.35, PL = 1.9
    const face = (s, m) => {
      const mir = s == 'B' ? '(justify mirror)' : ''
      let out = ''
      for (let i = 0; i < 7; i++) {
        const y = (-7.62 + 2.54 * i).toFixed(2)
        out += `(pad ${i + 1} smd roundrect (at ${m * -PX} ${y} ${p.r}) (size ${PL} 1.7) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.25) ${left[i]})\n`
        out += `(pad ${i + 8} smd roundrect (at ${m * PX} ${y} ${p.r}) (size ${PL} 1.7) (layers ${s}.Cu ${s}.Paste ${s}.Mask) (roundrect_rratio 0.25) ${right[i]})\n`
        out += `(fp_text user "${lname[i]}" (at ${m * -5.9} ${y} ${p.r}) (layer ${s}.SilkS) (effects (font (size 0.7 0.7) (thickness 0.12)) ${mir}))\n`
        out += `(fp_text user "${rname[i]}" (at ${m * 5.9} ${y} ${p.r}) (layer ${s}.SilkS) (effects (font (size 0.7 0.7) (thickness 0.12)) ${mir}))\n`
      }
      out += `
      (fp_line (start -8.89 -10.43) (end 8.89 -10.43) (layer ${s}.SilkS) (width 0.12))
      (fp_line (start -8.89 10.48) (end 8.89 10.48) (layer ${s}.SilkS) (width 0.12))
      (fp_text user "USB-C" (at 0 -8.3 ${p.r}) (layer ${s}.SilkS) (effects (font (size 0.8 0.8) (thickness 0.12)) ${mir}))
      (fp_line (start -9.6 -12.2) (end 9.6 -12.2) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start 9.6 -12.2) (end 9.6 10.7) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start 9.6 10.7) (end -9.6 10.7) (layer ${s}.CrtYd) (width 0.05))
      (fp_line (start -9.6 10.7) (end -9.6 -12.2) (layer ${s}.CrtYd) (width 0.05))
      (pad 15 thru_hole circle (at ${m * -4.445} -2.2225 ${p.r}) (size 1.35 1.35) (drill 0.8) (layers *.Cu *.Mask) ${p.BATN})
      (pad 16 thru_hole circle (at ${m * -4.445} -0.3175 ${p.r}) (size 1.35 1.35) (drill 0.8) (layers *.Cu *.Mask) ${p.BATP})
      ${p.NFC1 !== undefined ? `(pad 17 thru_hole circle (at ${m * 3.81} 9.2075 ${p.r}) (size 1.35 1.35) (drill 0.8) (layers *.Cu *.Mask) ${p.NFC1})
      (pad 18 thru_hole circle (at ${m * 5.715} 9.2075 ${p.r}) (size 1.35 1.35) (drill 0.8) (layers *.Cu *.Mask) ${p.NFC2})` : ''}
      `
      return out
    }
    const silkB = `
      (fp_text user "BAT-" (at -2.4 -2.22 ${p.r}) (layer B.SilkS) (effects (font (size 0.6 0.6) (thickness 0.1)) (justify mirror)))
      (fp_text user "BAT+" (at -2.4 -0.32 ${p.r}) (layer B.SilkS) (effects (font (size 0.6 0.6) (thickness 0.1)) (justify mirror)))`
    return `
    (module XIAO_nRF52840_SMD${p.reversible ? '_REV' : ''} (layer F.Cu) (tedit 0)
      ${p.at}
      (fp_text reference "${p.ref}" (at 0 3 ${p.r}) (layer F.SilkS) ${p.ref_hide} (effects (font (size 1 1) (thickness 0.15))))
      (fp_text value "XIAO_nRF52840" (at 0 5 ${p.r}) (layer F.Fab) (effects (font (size 1 1) (thickness 0.15))))
      ${face('F', 1)}
      ${p.reversible ? face('B', -1) : silkB}
    )
    `
  }
}

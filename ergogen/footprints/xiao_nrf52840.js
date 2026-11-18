// Seeed Studio XIAO nRF52840 (also fits the XIAO nRF52840 Sense / Plus), surface
// mounted flat on the PCB top via its castellated edge pads, USB-C toward local -y.
// The BAT+/BAT- pads on the XIAO's underside get plated through-holes so they can
// be soldered from the back of the keyboard PCB.
// Pad positions cross-checked against ebastler/marbastlib (CERN-OHL-P) and
// amacleod/weejock "Castellated XIAO with BAT+ and RST".
//
// Nets: D0..D10, V5 (VBUS), GND, V3 (3V3 out), BATP, BATN
module.exports = {
  params: {
    designator: 'MCU',
    D0: undefined, D1: undefined, D2: undefined, D3: undefined, D4: undefined,
    D5: undefined, D6: undefined, D7: undefined, D8: undefined, D9: undefined,
    D10: undefined, V5: undefined, GND: undefined, V3: undefined,
    BATP: undefined, BATN: undefined,
  },
  body: p => {
    const left = [p.D0, p.D1, p.D2, p.D3, p.D4, p.D5, p.D6]
    const right = [p.V5, p.GND, p.V3, p.D10, p.D9, p.D8, p.D7]
    const lname = ['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6']
    const rname = ['5V', 'G', '3V3', 'D10', 'D9', 'D8', 'D7']
    let pads = ''
    for (let i = 0; i < 7; i++) {
      const y = (-7.62 + 2.54 * i).toFixed(2)
      pads += `(pad ${i + 1} smd roundrect (at -8.55 ${y} ${p.r}) (size 2.6 1.7) (layers F.Cu F.Paste F.Mask) (roundrect_rratio 0.25) ${left[i]})\n`
      pads += `(pad ${i + 8} smd roundrect (at 8.55 ${y} ${p.r}) (size 2.6 1.7) (layers F.Cu F.Paste F.Mask) (roundrect_rratio 0.25) ${right[i]})\n`
      pads += `(fp_text user "${lname[i]}" (at -5.6 ${y} ${p.r}) (layer F.SilkS) (effects (font (size 0.7 0.7) (thickness 0.12))))\n`
      pads += `(fp_text user "${rname[i]}" (at 5.6 ${y} ${p.r}) (layer F.SilkS) (effects (font (size 0.7 0.7) (thickness 0.12))))\n`
    }
    return `
    (module XIAO_nRF52840_SMD (layer F.Cu) (tedit 0)
      ${p.at}
      (fp_text reference "${p.ref}" (at 0 3 ${p.r}) (layer F.SilkS) ${p.ref_hide} (effects (font (size 1 1) (thickness 0.15))))
      (fp_text value "XIAO_nRF52840" (at 0 5 ${p.r}) (layer F.Fab) (effects (font (size 1 1) (thickness 0.15))))
      (fp_line (start -8.89 -10.43) (end 8.89 -10.43) (layer F.SilkS) (width 0.12))
      (fp_line (start -8.89 10.48) (end 8.89 10.48) (layer F.SilkS) (width 0.12))
      (fp_line (start -4.5 -11.98) (end 4.5 -11.98) (layer F.Fab) (width 0.12))
      (fp_line (start -4.5 -11.98) (end -4.5 -4.64) (layer F.Fab) (width 0.12))
      (fp_line (start 4.5 -11.98) (end 4.5 -4.64) (layer F.Fab) (width 0.12))
      (fp_line (start -4.5 -4.64) (end 4.5 -4.64) (layer F.Fab) (width 0.12))
      (fp_text user "USB-C" (at 0 -8.3 ${p.r}) (layer F.SilkS) (effects (font (size 0.8 0.8) (thickness 0.12))))
      (fp_text user "BAT-" (at -2.0 -2.22 ${p.r}) (layer B.SilkS) (effects (font (size 0.7 0.7) (thickness 0.12)) (justify mirror)))
      (fp_text user "BAT+" (at -2.0 -0.32 ${p.r}) (layer B.SilkS) (effects (font (size 0.7 0.7) (thickness 0.12)) (justify mirror)))
      (fp_line (start -10.1 -12.2) (end 10.1 -12.2) (layer F.CrtYd) (width 0.05))
      (fp_line (start 10.1 -12.2) (end 10.1 10.7) (layer F.CrtYd) (width 0.05))
      (fp_line (start 10.1 10.7) (end -10.1 10.7) (layer F.CrtYd) (width 0.05))
      (fp_line (start -10.1 10.7) (end -10.1 -12.2) (layer F.CrtYd) (width 0.05))
      ${pads}
      (pad 15 thru_hole circle (at -4.445 -2.2225 ${p.r}) (size 1.35 1.35) (drill 0.8) (layers *.Cu *.Mask) ${p.BATN})
      (pad 16 thru_hole circle (at -4.445 -0.3175 ${p.r}) (size 1.35 1.35) (drill 0.8) (layers *.Cu *.Mask) ${p.BATP})
    )
    `
  }
}

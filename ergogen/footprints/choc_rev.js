// Kailh Choc v1 (PG1350, e.g. Kailh/LowproKB Sunset) with Kailh Choc hotswap
// sockets, REVERSIBLE: socket pads on both faces so one PCB serves both halves.
//   left half : switch on F, socket on B   (pins at (0,-5.95) and (+5,-3.75))
//   right half: board flipped, switch on B, socket on F (pins at (0,-5.95), (-5,-3.75))
// The inner socket pads are narrowed (1.6 x 2.2 mm) so they keep >0.4 mm from the
// opposite face's socket boss hole; the Kailh socket tab still lands on them.
// Nets: from = pad 1 (column), to = pad 2 (to the diode)
module.exports = {
  params: { designator: 'S', from: undefined, to: undefined, keycaps: true },
  body: p => {
    const pads = (s, m) => `
      (pad 1 smd rect (at ${m * -2.8} -6.15 ${p.r}) (size 1.6 2.2) (layers ${s}.Cu ${s}.Paste ${s}.Mask) ${p.from})
      (pad 2 smd rect (at ${m * 8.275} -3.75 ${p.r}) (size 2.6 2.6) (layers ${s}.Cu ${s}.Paste ${s}.Mask) ${p.to})
      (fp_line (start ${m * -7} -8.2) (end ${m * 1.5} -8.2) (layer ${s}.SilkS) (width 0.12))
      (fp_line (start ${m * 9.6} -1.3) (end ${m * 2.5} -1.3) (layer ${s}.SilkS) (width 0.12))`
    return `
    (module CHOC_V1_HOTSWAP_REV (layer F.Cu) (tedit 0)
      ${p.at}
      (fp_text reference "${p.ref}" (at 0 7.6 ${p.r}) (layer F.SilkS) ${p.ref_hide} (effects (font (size 1 1) (thickness 0.15))))
      (fp_text value "" (at 0 0) (layer F.Fab) hide (effects (font (size 1 1) (thickness 0.15))))
      ${p.keycaps ? `
      (fp_line (start -9 -8.5) (end 9 -8.5) (layer Dwgs.User) (width 0.15))
      (fp_line (start 9 -8.5) (end 9 8.5) (layer Dwgs.User) (width 0.15))
      (fp_line (start 9 8.5) (end -9 8.5) (layer Dwgs.User) (width 0.15))
      (fp_line (start -9 8.5) (end -9 -8.5) (layer Dwgs.User) (width 0.15))` : ''}
      (fp_line (start -7 -7) (end 7 -7) (layer Dwgs.User) (width 0.15))
      (fp_line (start 7 -7) (end 7 7) (layer Dwgs.User) (width 0.15))
      (fp_line (start 7 7) (end -7 7) (layer Dwgs.User) (width 0.15))
      (fp_line (start -7 7) (end -7 -7) (layer Dwgs.User) (width 0.15))
      (pad "" np_thru_hole circle (at 0 0) (size 3.429 3.429) (drill 3.429) (layers *.Cu *.Mask))
      (pad "" np_thru_hole circle (at 5.5 0) (size 1.7018 1.7018) (drill 1.7018) (layers *.Cu *.Mask))
      (pad "" np_thru_hole circle (at -5.5 0) (size 1.7018 1.7018) (drill 1.7018) (layers *.Cu *.Mask))
      (pad "" np_thru_hole circle (at 0 -5.95) (size 3 3) (drill 3) (layers *.Cu *.Mask))
      (pad "" np_thru_hole circle (at 5 -3.75) (size 3 3) (drill 3) (layers *.Cu *.Mask))
      (pad "" np_thru_hole circle (at -5 -3.75) (size 3 3) (drill 3) (layers *.Cu *.Mask))
      ${pads('B', 1)}
      ${pads('F', -1)}
    )
    `
  }
}

// Plain NPTH mounting hole (default: M2 clearance) with a keep-out ring on silk.
module.exports = {
  params: { designator: 'H', drill: 2.2 },
  body: p => `
    (module MountingHole_NPTH (layer F.Cu) (tedit 0)
      ${p.at}
      (fp_text reference "${p.ref}" (at 0 2.6) (layer F.SilkS) hide (effects (font (size 0.8 0.8) (thickness 0.12))))
      (fp_circle (center 0 0) (end ${p.drill / 2 + 1.0} 0) (layer F.CrtYd) (width 0.05))
      (fp_circle (center 0 0) (end ${p.drill / 2 + 1.0} 0) (layer B.CrtYd) (width 0.05))
      (pad "" np_thru_hole circle (at 0 0) (size ${p.drill} ${p.drill}) (drill ${p.drill}) (layers *.Cu *.Mask))
    )
  `
}

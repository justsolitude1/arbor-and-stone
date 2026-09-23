# Arbor & Stone

Marketing site for a luxury home builder, built around an interactive 3D model of **Residence No. 01**, a 4,650 sq ft modern forest home in cedar, stone and glass.

The opening screen offers two ways in. **Dive right in** flies up the drive, through the front doors and into the great room, then hands over control with a room bar (Entry, Great room, Kitchen, Primary suite, Loft, Patio, plus exterior and floor-plan views) and a day/dusk switch. **Take the tour** is the scroll story, where the camera flies along the driveway, around the corner, above the trees, down through a section cut of the main floor, into the double-height great room at dusk, and out onto the patio. Below the tour are the specs, materials, a render gallery, the build process, a "Step inside" band and an enquiry form.

## Structure

| Path | What it is |
| --- | --- |
| `index.html` | The built site. A single file with the model and images inlined. This is what GitHub Pages serves. |
| `src/index.src.html` | Editable source with `{{GLB}}` and `{{IMG_*}}` placeholders. |
| `src/build.py` | Inlines `assets/` into the source and writes `index.html`. |
| `assets/house.glb` | Web-optimised 3D model (about 1.9 MB). |
| `assets/renders/` | Cycles renders used in the gallery. |
| `blender/build_house.py` | Procedurally builds the house, site and trees in Blender 5.x and renders the views. |
| `blender/export_glb.py` | Exports the Blender scene to `assets/house.glb`. |
| `blender/ModernSanctuary.blend` | The Blender scene. |

## Editing

```bash
# change copy or styles in src/index.src.html, then:
python src/build.py
```

To change the house itself, edit `blender/build_house.py`, then:

```bash
blender -b --python blender/build_house.py -- front,corner,aerial,rear,living 96
blender -b blender/ModernSanctuary.blend --python blender/export_glb.py
```

`export_glb.py` writes to a `viewer/` folder next to the `.blend` file. Copy `house.glb` from there into `assets/` and run `python src/build.py`.

## Before going live

- **Placeholders:** the company name, email address, "Price on request" and the process copy are placeholders.
- **Enquiry form:** the form validates input but isn't connected to anything. Wire the submit handler to your inbox or CRM.
- **Dependencies:** three.js, GSAP and Google Fonts load from public CDNs.

Residence No. 01 is a design visualisation. Areas are approximate and furnishings are illustrative.
